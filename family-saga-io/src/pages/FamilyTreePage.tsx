import { useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Tag,
  Modal,
  Breadcrumb,
  Form,
  Input,
  Select,
  InputNumber,
  Radio,
} from 'antd';
import { HomeOutlined, TeamOutlined, UserOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { familyData, familyInfo, type FamilyMember } from '@/data/familyMockData';
import FamilyTreeNode from '@/components/FamilyTreeNode';
import * as XLSX from 'xlsx';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import ThemeToggle from '@/components/ThemeToggle';

const FamilyTreePage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [members, setMembers] = useState<FamilyMember[]>(familyData);
  const [selectedMember, setSelectedMember] = useState<FamilyMember | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<FamilyMember | null>(null);

  const root = members.find((m) => !m.parentId)!;

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
            {t('familyTree.pageTitle', { surname: familyInfo.surname })}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <Tag color="gold" style={{ fontFamily: 'var(--font-body)' }}>
            {t('familyTree.generations', { count: familyInfo.totalGenerations })}
          </Tag>
          <Tag
            style={{
              fontFamily: 'var(--font-body)',
              color: 'hsl(0, 45%, 35%)',
              borderColor: 'hsl(0, 45%, 35%)',
            }}
          >
            {t('familyTree.members', { count: familyInfo.totalMembers })}
          </Tag>
          <LanguageSwitcher />
          <ThemeToggle />
          <Button type="primary" onClick={handleExportExcel}>
            {t('familyTree.exportExcel')}
          </Button>
        </div>
      </header>

      {/* Family Info Banner */}
      <div className="gold-gradient px-6 py-4">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-parchment text-sm font-body">{t('familyTree.origin', { origin: familyInfo.origin })}</p>
            <p className="text-parchment/80 text-sm italic mt-1">"{familyInfo.motto}"</p>
          </div>
          <div className="text-parchment text-sm">
            {t('familyTree.established', { year: familyInfo.established })}
          </div>
        </div>
      </div>

      {/* Tree View */}
      <div className="p-6 overflow-x-auto">
        <div className="min-w-[800px] flex justify-center py-8">
          {renderTree(root)}
        </div>
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
