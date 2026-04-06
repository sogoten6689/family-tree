import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Radio,
} from 'antd';
import { UserOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { familyData, familyInfo, type FamilyMember } from '@/data/familyMockData';
import { BalkanFamilyTreeView, type BalkanNode } from '@/components/BalkanFamilyTreeView';
import FamilyTreeNode from '@/components/FamilyTreeNode';
import * as XLSX from 'xlsx';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import ThemeToggle from '@/components/ThemeToggle';

type BackendPerson = {
  id: string;
  full_name: string;
  gender?: string | null;
  birth_year?: number | null;
  death_year?: number | null;
};

type BackendRelationship = {
  from_id: string;
  to_id: string;
  type: string;
};

type BackendAnalysisPayload = {
  balkan_nodes?: BalkanNode[];
  gemini_error?: string | null;
  extraction?: {
    people?: BackendPerson[];
    relationships?: BackendRelationship[];
  };
};

const inferGenderFromName = (name: string): 'male' | 'female' => {
  return /\bThị\b/i.test(name) ? 'female' : 'male';
};

const normalizeGender = (gender: string | null | undefined, name: string): 'male' | 'female' => {
  const raw = (gender ?? '').toLowerCase();
  if (raw === 'f' || raw === 'female' || raw === 'nu' || raw === 'nữ') {
    return 'female';
  }
  if (raw === 'm' || raw === 'male' || raw === 'nam') {
    return 'male';
  }
  return inferGenderFromName(name);
};

const buildMembersFromBackend = (payload: BackendAnalysisPayload): { members: FamilyMember[]; info: typeof familyInfo } | null => {
  const people = payload.extraction?.people ?? [];
  const relationships = payload.extraction?.relationships ?? [];
  if (people.length === 0) {
    return null;
  }

  const personMap = new Map<string, BackendPerson>(people.map((p) => [p.id, p]));
  const childrenMap = new Map<string, string[]>();
  const parentMap = new Map<string, string>();
  const spouseMap = new Map<string, string>();

  relationships.forEach((r) => {
    if (r.type === 'parent_of') {
      if (!childrenMap.has(r.from_id)) {
        childrenMap.set(r.from_id, []);
      }
      const siblings = childrenMap.get(r.from_id)!;
      if (!siblings.includes(r.to_id)) {
        siblings.push(r.to_id);
      }
      if (!parentMap.has(r.to_id)) {
        parentMap.set(r.to_id, r.from_id);
      }
    }

    if (r.type === 'spouse_of') {
      if (!spouseMap.has(r.from_id)) {
        spouseMap.set(r.from_id, r.to_id);
      }
      if (!spouseMap.has(r.to_id)) {
        spouseMap.set(r.to_id, r.from_id);
      }
    }
  });

  const roots = people
    .map((p) => p.id)
    .filter((id) => !parentMap.has(id));

  const generationMap = new Map<string, number>();
  const queue: Array<{ id: string; gen: number }> = [];

  roots.forEach((id) => {
    generationMap.set(id, 1);
    queue.push({ id, gen: 1 });
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    (childrenMap.get(current.id) ?? []).forEach((childId) => {
      const nextGen = current.gen + 1;
      if (!generationMap.has(childId) || nextGen < generationMap.get(childId)!) {
        generationMap.set(childId, nextGen);
        queue.push({ id: childId, gen: nextGen });
      }
    });
  }

  const members: FamilyMember[] = people.map((p) => {
    const spouseId = spouseMap.get(p.id);
    const spouseName = spouseId ? personMap.get(spouseId)?.full_name : undefined;
    const birthYear = typeof p.birth_year === 'number' ? p.birth_year : 0;
    const deathYear = typeof p.death_year === 'number' ? p.death_year : undefined;

    return {
      id: p.id,
      name: p.full_name,
      birthYear,
      deathYear,
      gender: normalizeGender(p.gender, p.full_name),
      generation: generationMap.get(p.id) ?? 1,
      spouseName,
      children: childrenMap.get(p.id) ?? [],
      parentId: parentMap.get(p.id),
    };
  });

  const maxGeneration = Math.max(...members.map((m) => m.generation));
  const knownBirthYears = members
    .map((m) => m.birthYear)
    .filter((y) => Number.isFinite(y) && y > 0);

  const rootName = members.find((m) => !m.parentId)?.name ?? members[0].name;
  const inferredSurname = rootName.split(' ')[0] || familyInfo.surname;

  const info: typeof familyInfo = {
    surname: inferredSurname,
    origin: 'Từ dữ liệu phân tích tài liệu',
    motto: 'Tự động dựng từ backend JSON',
    totalGenerations: maxGeneration,
    totalMembers: members.length,
    established: knownBirthYears.length > 0 ? Math.min(...knownBirthYears) : familyInfo.established,
  };

  return { members, info };
};

const FamilyTreePage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [members, setMembers] = useState<FamilyMember[]>(familyData);
  const [runtimeInfo, setRuntimeInfo] = useState(familyInfo);
  const [isUsingBackendData, setIsUsingBackendData] = useState(false);
  const [balkanNodes, setBalkanNodes] = useState<BalkanNode[]>([]);
  const [balkanGeminiError, setBalkanGeminiError] = useState<string | null>(null);
  const [isBalkanPayload, setIsBalkanPayload] = useState(false);
  const [selectedMember, setSelectedMember] = useState<FamilyMember | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<FamilyMember | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('family-tree.analysis');
      if (!raw) {
        return;
      }

      const parsed = JSON.parse(raw) as BackendAnalysisPayload;

      if ('balkan_nodes' in parsed && Array.isArray(parsed.balkan_nodes)) {
        const nodes = parsed.balkan_nodes;
        setBalkanNodes(nodes);
        setBalkanGeminiError(parsed.gemini_error ?? null);
        setIsBalkanPayload(true);
        setIsUsingBackendData(true);
        setRuntimeInfo((prev) => ({
          ...prev,
          totalMembers: nodes.length,
          totalGenerations: Math.max(1, prev.totalGenerations),
          origin: 'Từ phân tích tài liệu (BALKAN)',
          motto: 'Dữ liệu Gemini chuẩn hoá',
        }));
        return;
      }

      const built = buildMembersFromBackend(parsed);
      if (!built) {
        return;
      }

      setMembers(built.members);
      setRuntimeInfo(built.info);
      setIsUsingBackendData(true);
    } catch {
      // Keep mock data as fallback
    }
  }, []);

  const root = members.find((m) => !m.parentId) ?? members[0];

  const getChildren = (parentId: string) =>
    members.filter((m) => m.parentId === parentId);

  const handleSelect = (member: FamilyMember) => {
    const fullMember = members.find((m) => m.id === member.id) ?? member;
    setSelectedMember(fullMember);
    setDetailOpen(true);
  };

  const handleExportExcel = () => {
    const data = members.map((m) => ({
      ID: m.id,
      HoTen: m.name,
      NamSinh: m.birthYear,
      NamMat: m.deathYear ?? '',
      GioiTinh: m.gender === 'male' ? 'Nam' : 'Nữ',
      DoiThu: m.generation,
      VoChong: m.spouseName ?? '',
      DanhXung: m.title ?? '',
      TieuSu: m.bio ?? '',
      ChaMe: m.parentId ?? '',
      ConCai: (m.children ?? []).join('|'),
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'GiaPha');

    XLSX.writeFile(wb, 'family-tree.xlsx');
  };

  const handleEditSubmit = (values: any) => {
    if (!editingMember) return;

    const oldParentId = editingMember.parentId;
    const newParentId = values.parentId || undefined;

    let updatedMember: FamilyMember = {
      ...editingMember,
      ...values,
      parentId: newParentId,
    };

    const nextMembers = members.map((m) => ({ ...m }));

    // Update generation if parent changed
    if (newParentId) {
      const newParent = nextMembers.find((m) => m.id === newParentId);
      if (newParent) {
        updatedMember = {
          ...updatedMember,
          generation: newParent.generation + 1,
        };
      }
    }

    // Sync parent children list when parent changes
    if (oldParentId && oldParentId !== newParentId) {
      const oldParent = nextMembers.find((m) => m.id === oldParentId);
      if (oldParent?.children) {
        oldParent.children = oldParent.children.filter((id) => id !== updatedMember.id);
      }
    }

    if (newParentId && newParentId !== oldParentId) {
      const newParent = nextMembers.find((m) => m.id === newParentId);
      if (newParent) {
        const children = newParent.children ?? [];
        if (!children.includes(updatedMember.id)) {
          newParent.children = [...children, updatedMember.id];
        }
      }
    }

    const idx = nextMembers.findIndex((m) => m.id === updatedMember.id);
    if (idx !== -1) {
      nextMembers[idx] = updatedMember;
    }

    setMembers(nextMembers);
    setSelectedMember(updatedMember);
    setEditingMember(null);
    setEditOpen(false);
  };

  const renderTree = (member: FamilyMember): React.ReactNode => {
    const children = getChildren(member.id);
    return (
      <div key={member.id} className="flex flex-col items-center">
        <FamilyTreeNode
          member={member}
          onSelect={handleSelect}
          isSelected={selectedMember?.id === member.id}
        />
        {children.length > 0 && (
          <>
            <div className="tree-connector-v h-6" />
            <div className="flex gap-4 relative">
              {children.length > 1 && (
                <div
                  className="tree-connector-h absolute top-0"
                  style={{
                    width: `calc(100% - 180px)`,
                    left: `90px`,
                  }}
                />
              )}
              {children.map((child) => (
                <div key={child.id} className="flex flex-col items-center">
                  <div className="tree-connector-v h-6" />
                  {renderTree(child)}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header
        className="px-6 py-4 flex items-center justify-between border-b"
        style={{ borderColor: 'hsl(36, 30%, 80%)' }}
      >
        <div className="flex items-center gap-4">
          <Button
            icon={<ArrowLeftOutlined />}
            type="text"
            onClick={() => navigate('/')}
            style={{ color: 'hsl(36, 70%, 42%)' }}
          >
            {t('common.backHome')}
          </Button>
          <div className="section-divider w-px h-6 mx-2" style={{ width: 1, background: 'hsl(36, 30%, 80%)' }} />
          <h1 className="text-xl font-display font-bold text-foreground">
            {t('familyTree.pageTitle', { surname: runtimeInfo.surname })}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <Tag color="gold" style={{ fontFamily: 'var(--font-body)' }}>
            {t('familyTree.generations', { count: runtimeInfo.totalGenerations })}
          </Tag>
          <Tag
            style={{
              fontFamily: 'var(--font-body)',
              color: 'hsl(0, 45%, 35%)',
              borderColor: 'hsl(0, 45%, 35%)',
            }}
          >
            {t('familyTree.members', { count: runtimeInfo.totalMembers })}
          </Tag>
          <LanguageSwitcher />
          <ThemeToggle />
          {balkanNodes.length === 0 && (
            <Button type="primary" onClick={handleExportExcel}>
              {t('familyTree.exportExcel')}
            </Button>
          )}
        </div>
      </header>

      {/* Family Info Banner */}
      <div className="gold-gradient px-6 py-4">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-parchment text-sm font-body">{t('familyTree.origin', { origin: runtimeInfo.origin })}</p>
            <p className="text-parchment/80 text-sm italic mt-1">"{runtimeInfo.motto}"</p>
          </div>
          <div className="text-parchment text-sm">
            {t('familyTree.established', { year: runtimeInfo.established })}
          </div>
        </div>
      </div>

      {/* Tree View */}
      <div className="p-6 overflow-x-auto">
        {isUsingBackendData && isBalkanPayload && (
          <Alert
            type="success"
            showIcon
            message="Đang hiển thị cây BALKAN (Gemini)"
            description="Dữ liệu từ phân tích ở trang Document Reader."
            className="mb-6"
          />
        )}
        {balkanGeminiError && (
          <Alert
            type="warning"
            showIcon
            message="Cảnh báo chuẩn hoá"
            description={balkanGeminiError}
            className="mb-6"
          />
        )}
        {isBalkanPayload ? (
          balkanNodes.length > 0 ? (
            <div className="max-w-[1400px] mx-auto">
              <BalkanFamilyTreeView nodes={balkanNodes} height={640} />
            </div>
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Chưa có node BALKAN — kiểm tra Gemini / GOOGLE_API_KEY."
            />
          )
        ) : (
          <div className="min-w-[800px] flex justify-center py-8">
            {root ? renderTree(root) : null}
          </div>
        )}
      </div>

      {/* Member Detail Modal */}
      <Modal
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailOpen(false)}>
            {t('familyTree.close')}
          </Button>,
          selectedMember && (
            <Button
              key="edit"
              type="primary"
              onClick={() => {
                setEditingMember(selectedMember);
                setEditOpen(true);
              }}
            >
              {t('familyTree.editMember')}
            </Button>
          ),
        ]}
        title={
          <span className="font-display text-lg">
            <UserOutlined className="mr-2" />
            {t('familyTree.modalDetailTitle')}
          </span>
        }
        width={500}
      >
        {selectedMember && (
          <div className="py-4">
            <div className="flex items-center gap-4 mb-6">
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center text-2xl"
                style={{
                  background: selectedMember.gender === 'male' ? 'hsl(36, 70%, 42%)' : 'hsl(0, 45%, 35%)',
                  color: 'hsl(39, 50%, 96%)',
                }}
              >
                {selectedMember.gender === 'male' ? '♂' : '♀'}
              </div>
              <div>
                <h3 className="text-xl font-display font-bold text-foreground">{selectedMember.name}</h3>
                {selectedMember.title && (
                  <Tag color="gold" className="mt-1">{selectedMember.title}</Tag>
                )}
              </div>
            </div>

            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label={t('familyTree.birthYear')}>{selectedMember.birthYear}</Descriptions.Item>
              {selectedMember.deathYear && (
                <Descriptions.Item label={t('familyTree.deathYear')}>{selectedMember.deathYear}</Descriptions.Item>
              )}
              <Descriptions.Item label={t('familyTree.gender')}>
                {selectedMember.gender === 'male' ? t('familyTree.male') : t('familyTree.female')}
              </Descriptions.Item>
              <Descriptions.Item label={t('familyTree.generation')}>{selectedMember.generation}</Descriptions.Item>
              {selectedMember.spouseName && (
                <Descriptions.Item label={t('familyTree.spouse')}>{selectedMember.spouseName}</Descriptions.Item>
              )}
              {selectedMember.children && (
                <Descriptions.Item label={t('familyTree.numChildren')}>{selectedMember.children.length}</Descriptions.Item>
              )}
            </Descriptions>

            {selectedMember.bio && (
              <div className="mt-4 p-3 rounded-lg" style={{ background: 'hsl(39, 40%, 93%)' }}>
                <p className="text-sm text-muted-foreground italic">"{selectedMember.bio}"</p>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Edit Member Modal */}
      <Modal
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditingMember(null);
        }}
        footer={null}
        title={
          <span className="font-display text-lg">
            <UserOutlined className="mr-2" />
            {t('familyTree.modalEditTitle')}
          </span>
        }
        width={600}
        destroyOnClose
      >
        {editingMember && (
          <Form
            layout="vertical"
            initialValues={{
              name: editingMember.name,
              birthYear: editingMember.birthYear,
              deathYear: editingMember.deathYear,
              gender: editingMember.gender,
              generation: editingMember.generation,
              spouseName: editingMember.spouseName,
              title: editingMember.title,
              bio: editingMember.bio,
              parentId: editingMember.parentId,
            }}
            onFinish={handleEditSubmit}
          >
            <Form.Item
              label={t('familyTree.fullName')}
              name="name"
              rules={[{ required: true, message: t('familyTree.validationName') }]}
            >
              <Input />
            </Form.Item>

            <div className="grid grid-cols-2 gap-4">
              <Form.Item
                label={t('familyTree.birthYear')}
                name="birthYear"
                rules={[{ required: true, message: t('familyTree.validationBirthYear') }]}
              >
                <InputNumber className="w-full" />
              </Form.Item>

              <Form.Item label={t('familyTree.deathYear')} name="deathYear">
                <InputNumber className="w-full" />
              </Form.Item>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Form.Item
                label={t('familyTree.gender')}
                name="gender"
                rules={[{ required: true, message: t('familyTree.validationGender') }]}
              >
                <Radio.Group>
                  <Radio value="male">{t('familyTree.male')}</Radio>
                  <Radio value="female">{t('familyTree.female')}</Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item label={t('familyTree.generation')} name="generation">
                <InputNumber className="w-full" />
              </Form.Item>
            </div>

            <Form.Item label={t('familyTree.spouseLabel')} name="spouseName">
              <Input />
            </Form.Item>

            <Form.Item label={t('familyTree.titleField')} name="title">
              <Input />
            </Form.Item>

            <Form.Item label={t('familyTree.bio')} name="bio">
              <Input.TextArea rows={3} />
            </Form.Item>

            <Form.Item label={t('familyTree.parent')} name="parentId">
              <Select allowClear placeholder={t('familyTree.selectParent')}>
                {members
                  .filter((m) => m.id !== editingMember.id)
                  .map((m) => (
                    <Select.Option key={m.id} value={m.id}>
                      {t('familyTree.parentLabel', { name: m.name, gen: m.generation })}
                    </Select.Option>
                  ))}
              </Select>
            </Form.Item>

            <div className="flex justify-end gap-3 mt-4">
              <Button
                onClick={() => {
                  setEditOpen(false);
                  setEditingMember(null);
                }}
              >
                {t('familyTree.cancel')}
              </Button>
              <Button type="primary" htmlType="submit">
                {t('familyTree.save')}
              </Button>
            </div>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default FamilyTreePage;
