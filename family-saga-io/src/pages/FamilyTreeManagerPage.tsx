import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Avatar,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Row,
  Select,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  BranchesOutlined,
  CloudDownloadOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import FamilyTreeNode from '@/components/FamilyTreeNode';
import { BalkanFamilyTreeView } from '@/components/BalkanFamilyTreeView';
import { FamilyTreeDocumentsPanel } from '@/components/documents/FamilyTreeDocumentsPanel';
import type { FamilyMember } from '@/data/familyMockData';
import {
  createFamilyTree,
  crawlAndSyncVietnamGiaPha,
  createLink,
  createNode,
  deleteLink,
  deleteFamilyTree,
  getFamilyTree,
  listFamilyTrees,
  removeNode,
  replaceFamilyTreeDocument,
  updateFamilyTree,
  updateNode,
  type BalkanNode,
  type FamilyTreeDocument,
  type FamilyTreeSummary,
  type Gender,
} from '@/lib/familyTreeApi';

type TreeFormValues = {
  name: string;
  description?: string;
};

type MemberFormValues = {
  name: string;
  gender: Gender;
  birthYear?: number;
  deathYear?: number;
  title?: string;
  bio?: string;
  fatherId?: number;
  motherId?: number;
  spouseIds?: number[];
};

type LinkFormValues = {
  type: 'spouse_of' | 'parent_of';
  fromId: number;
  toId: number;
  side?: 'fid' | 'mid';
};

type CrawlFormValues = {
  startId: number;
  endId: number;
  delaySeconds?: number;
  syncDb: boolean;
};

const inferGenderFromName = (name: string): Gender => {
  return /\bThị\b/i.test(name) ? 'female' : 'male';
};

const normalizeGender = (gender: string | null | undefined, name: string): Gender => {
  const raw = (gender ?? '').toLowerCase();
  if (raw === 'female' || raw === 'f' || raw === 'nữ' || raw === 'nu') return 'female';
  if (raw === 'male' || raw === 'm' || raw === 'nam') return 'male';
  return inferGenderFromName(name);
};

const toFamilyMembers = (nodes: BalkanNode[]): FamilyMember[] => {
  const personMap = new Map<string, BalkanNode>();
  const childrenMap = new Map<string, Set<string>>();
  const parentMap = new Map<string, string>();
  const spouseMap = new Map<string, Set<string>>();

  nodes.forEach((node) => {
    personMap.set(String(node.id), node);
  });

  nodes.forEach((node) => {
    const nodeId = String(node.id);
    if (typeof node.fid === 'number') {
      const parentId = String(node.fid);
      if (!childrenMap.has(parentId)) childrenMap.set(parentId, new Set());
      childrenMap.get(parentId)!.add(nodeId);
      if (!parentMap.has(nodeId)) parentMap.set(nodeId, parentId);
    }
    if (typeof node.mid === 'number') {
      const parentId = String(node.mid);
      if (!childrenMap.has(parentId)) childrenMap.set(parentId, new Set());
      childrenMap.get(parentId)!.add(nodeId);
      if (!parentMap.has(nodeId)) parentMap.set(nodeId, parentId);
    }

    if (Array.isArray(node.pids)) {
      node.pids.forEach((spouseIdRaw) => {
        const spouseId = String(spouseIdRaw);
        if (!spouseMap.has(nodeId)) spouseMap.set(nodeId, new Set());
        spouseMap.get(nodeId)!.add(spouseId);
      });
    }
  });

  const childIds = new Set(parentMap.keys());
  const roots = nodes.map((node) => String(node.id)).filter((id) => !childIds.has(id));
  const generationMap = new Map<string, number>();
  const queue: Array<{ id: string; generation: number }> = [];

  roots.forEach((id) => {
    generationMap.set(id, 1);
    queue.push({ id, generation: 1 });
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    const childIdsOfCurrent = childrenMap.get(current.id) ?? new Set<string>();
    childIdsOfCurrent.forEach((childId) => {
      const nextGeneration = current.generation + 1;
      if (!generationMap.has(childId) || nextGeneration < generationMap.get(childId)!) {
        generationMap.set(childId, nextGeneration);
        queue.push({ id: childId, generation: nextGeneration });
      }
    });
  }

  return nodes.map((node) => {
    const nodeId = String(node.id);
    const spouseIds = Array.from(spouseMap.get(nodeId) ?? new Set<string>());
    const spouseName = spouseIds.length > 0 ? personMap.get(spouseIds[0])?.name : undefined;
    const parentId = parentMap.get(nodeId);

    return {
      id: nodeId,
      name: node.name,
      birthYear: typeof node.birthYear === 'number' ? node.birthYear : 0,
      deathYear: typeof node.deathYear === 'number' ? node.deathYear : undefined,
      gender: normalizeGender(node.gender, node.name),
      generation: generationMap.get(nodeId) ?? 1,
      spouseName,
      title: typeof node.title === 'string' ? node.title : undefined,
      bio: typeof node.bio === 'string' ? node.bio : undefined,
      children: Array.from(childrenMap.get(nodeId) ?? new Set()),
      parentId,
      avatar: typeof node.avatar === 'string' ? node.avatar : undefined,
    };
  });
};

const toTreeStats = (nodes: BalkanNode[]) => {
  const generations = new Set<number>();
  const childIds = new Set<number>();

  nodes.forEach((node) => {
    if (typeof node.fid === 'number') childIds.add(node.id);
    if (typeof node.mid === 'number') childIds.add(node.id);
  });

  const rootIds = nodes.map((node) => node.id).filter((id) => !childIds.has(id));
  const generationMap = new Map<number, number>();
  const queue: Array<{ id: number; generation: number }> = [];

  rootIds.forEach((id) => {
    generationMap.set(id, 1);
    queue.push({ id, generation: 1 });
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    generations.add(current.generation);

    nodes
      .filter((node) => node.fid === current.id || node.mid === current.id)
      .forEach((child) => {
        const nextGeneration = current.generation + 1;
        if (!generationMap.has(child.id) || nextGeneration < generationMap.get(child.id)!) {
          generationMap.set(child.id, nextGeneration);
          queue.push({ id: child.id, generation: nextGeneration });
        }
      });
  }

  if (generations.size === 0 && nodes.length > 0) {
    generations.add(1);
  }

  const birthYears = nodes
    .map((node) => (typeof node.birthYear === 'number' ? node.birthYear : undefined))
    .filter((year): year is number => typeof year === 'number' && year > 0);

  return {
    totalMembers: nodes.length,
    totalGenerations: Math.max(1, generations.size || 1),
    established: birthYears.length > 0 ? Math.min(...birthYears) : 0,
  };
};

const FamilyTreeManagerPage = () => {
  const { t } = useTranslation();

  const [trees, setTrees] = useState<FamilyTreeSummary[]>([]);
  const [currentTree, setCurrentTree] = useState<FamilyTreeDocument | null>(null);
  const [selectedTreeId, setSelectedTreeId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [loadingTrees, setLoadingTrees] = useState(false);
  const [loadingTree, setLoadingTree] = useState(false);
  const [savingTree, setSavingTree] = useState(false);
  const [savingNode, setSavingNode] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [treeModalOpen, setTreeModalOpen] = useState(false);
  const [editingTree, setEditingTree] = useState<FamilyTreeDocument | null>(null);
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<BalkanNode | null>(null);
  const [savingLink, setSavingLink] = useState(false);
  const [jsonViewerOpen, setJsonViewerOpen] = useState(false);
  const [jsonEditorOpen, setJsonEditorOpen] = useState(false);
  const [savingJson, setSavingJson] = useState(false);
  const [jsonDraft, setJsonDraft] = useState('');
  const [crawlModalOpen, setCrawlModalOpen] = useState(false);
  const [crawlingData, setCrawlingData] = useState(false);
  const [treeSearchKeyword, setTreeSearchKeyword] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);

  const [treeForm] = Form.useForm<TreeFormValues>();
  const [memberForm] = Form.useForm<MemberFormValues>();
  const [createLinkForm] = Form.useForm<LinkFormValues>();
  const [deleteLinkForm] = Form.useForm<LinkFormValues>();
  const [crawlForm] = Form.useForm<CrawlFormValues>();

  const members = useMemo(() => toFamilyMembers(currentTree?.nodes ?? []), [currentTree]);
  const stats = useMemo(() => toTreeStats(currentTree?.nodes ?? []), [currentTree]);
  const selectedMember = useMemo(
    () => members.find((member) => Number(member.id) === selectedNodeId) ?? null,
    [members, selectedNodeId],
  );
  const selectedNode = useMemo(
    () => currentTree?.nodes.find((node) => Number(node.id) === selectedNodeId) ?? null,
    [currentTree, selectedNodeId],
  );

  const loadTrees = async (preferredId?: string) => {
    setLoadingTrees(true);
    setPageError(null);
    try {
      const response = await listFamilyTrees();
      setTrees(response.items);

      if (preferredId) {
        setSelectedTreeId(preferredId);
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Cannot load trees');
      setTrees([]);
      setSelectedTreeId(null);
      setCurrentTree(null);
      setDrawerOpen(false);
    } finally {
      setLoadingTrees(false);
    }
  };

  useEffect(() => {
    void loadTrees();
  }, []);

  const reloadCurrentTree = async () => {
    if (!selectedTreeId) return;
    setLoadingTree(true);
    try {
      const tree = await getFamilyTree(selectedTreeId);
      setCurrentTree(tree);
      setTrees((prev) =>
        prev.map((item) =>
          item.id === tree.id
            ? {
                ...item,
                name: tree.name,
                description: tree.description,
                updated_at: tree.updated_at,
                node_count: tree.nodes.length,
              }
            : item,
        ),
      );
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Cannot load tree detail');
    } finally {
      setLoadingTree(false);
    }
  };

  const openTreeDetail = async (treeId: string) => {
    setSelectedTreeId(treeId);
    setSelectedNodeId(null);
    setDrawerOpen(true);
    setLoadingTree(true);
    setPageError(null);
    try {
      const tree = await getFamilyTree(treeId);
      setCurrentTree(tree);
    } catch (error) {
      setCurrentTree(null);
      setPageError(error instanceof Error ? error.message : 'Cannot load tree detail');
    } finally {
      setLoadingTree(false);
    }
  };

  const closeTreeDrawer = () => {
    setDrawerOpen(false);
    setSelectedNodeId(null);
  };

  const openCreateTreeModal = () => {
    setEditingTree(null);
    treeForm.setFieldsValue({ name: '', description: '' });
    setTreeModalOpen(true);
  };

  const openEditTreeModal = () => {
    if (!currentTree) return;
    setEditingTree(currentTree);
    treeForm.setFieldsValue({ name: currentTree.name, description: currentTree.description ?? '' });
    setTreeModalOpen(true);
  };

  const submitTreeForm = async (values: TreeFormValues) => {
    setSavingTree(true);
    try {
      if (editingTree) {
        const updated = await updateFamilyTree(editingTree.id, values);
        setTreeModalOpen(false);
        setEditingTree(null);
        setCurrentTree(updated);
        await loadTrees(updated.id);
      } else {
        const created = await createFamilyTree({
          name: values.name,
          description: values.description || undefined,
        });
        setTreeModalOpen(false);
        setEditingTree(null);
        await loadTrees(created.id);
        await openTreeDetail(created.id);
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Cannot save tree');
    } finally {
      setSavingTree(false);
    }
  };

  const handleDeleteTree = () => {
    if (!currentTree) return;
    Modal.confirm({
      title: t('familyTree.deleteTreeTitle', { defaultValue: 'Xóa cây gia phả' }),
      content: t('familyTree.deleteTreeConfirm', {
        defaultValue: 'Bạn có chắc muốn xóa cây này không? Hành động này không thể hoàn tác.',
      }),
      okText: t('familyTree.delete', { defaultValue: 'Xóa' }),
      okButtonProps: { danger: true },
      cancelText: t('familyTree.cancel', { defaultValue: 'Hủy' }),
      onOk: async () => {
        try {
          await deleteFamilyTree(currentTree.id);
          const remaining = trees.filter((item) => item.id !== currentTree.id);
          setTrees(remaining);
          setCurrentTree(null);
          setSelectedNodeId(null);
          setSelectedTreeId(null);
          setDrawerOpen(false);
        } catch (error) {
          setPageError(error instanceof Error ? error.message : String(error));
        }
      },
    });
  };

  const openCreateMemberModal = () => {
    if (!currentTree) return;
    setEditingNode(null);
    memberForm.resetFields();
    memberForm.setFieldsValue({
      gender: 'male',
      spouseIds: [],
    });
    setMemberModalOpen(true);
  };

  const openEditMemberModal = (node: BalkanNode) => {
    setEditingNode(node);
    memberForm.setFieldsValue({
      name: node.name,
      gender: normalizeGender(node.gender, node.name),
      birthYear: node.birthYear,
      deathYear: node.deathYear,
      title: typeof node.title === 'string' ? node.title : undefined,
      bio: typeof node.bio === 'string' ? node.bio : undefined,
      fatherId: node.fid,
      motherId: node.mid,
      spouseIds: Array.isArray(node.pids) ? node.pids : [],
    });
    setMemberModalOpen(true);
  };

  const submitMemberForm = async (values: MemberFormValues) => {
    if (!currentTree) return;
    setSavingNode(true);
    try {
      const payload = {
        name: values.name,
        gender: values.gender,
        birthYear: values.birthYear,
        deathYear: values.deathYear,
        title: values.title || undefined,
        bio: values.bio || undefined,
        fid: values.fatherId ?? undefined,
        mid: values.motherId ?? undefined,
        pids: values.spouseIds && values.spouseIds.length > 0 ? values.spouseIds : undefined,
      };

      if (editingNode) {
        await updateNode(currentTree.id, Number(editingNode.id), payload);
      } else {
        await createNode(currentTree.id, payload);
      }

      setMemberModalOpen(false);
      setEditingNode(null);
      await reloadCurrentTree();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Cannot save member');
    } finally {
      setSavingNode(false);
    }
  };

  const handleDeleteMember = (node: BalkanNode) => {
    if (!currentTree) return;
    Modal.confirm({
      title: t('familyTree.deleteMemberTitle', { defaultValue: 'Xóa thành viên' }),
      content: t('familyTree.deleteMemberConfirm', {
        defaultValue: 'Xóa thành viên này sẽ đồng thời dọn các liên kết quan hệ liên quan.',
      }),
      okText: t('familyTree.delete', { defaultValue: 'Xóa' }),
      okButtonProps: { danger: true },
      cancelText: t('familyTree.cancel', { defaultValue: 'Hủy' }),
      onOk: async () => {
        try {
          await removeNode(currentTree.id, Number(node.id));
          setSelectedNodeId((prev) => (prev === Number(node.id) ? null : prev));
          await reloadCurrentTree();
        } catch (error) {
          setPageError(error instanceof Error ? error.message : String(error));
        }
      },
    });
  };

  const submitCreateLinkForm = async (values: LinkFormValues) => {
    if (!currentTree) return;
    setSavingLink(true);
    try {
      await createLink(currentTree.id, {
        type: values.type,
        from_id: values.fromId,
        to_id: values.toId,
        side: values.type === 'parent_of' ? values.side : undefined,
      });
      createLinkForm.resetFields(['fromId', 'toId']);
      await reloadCurrentTree();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Cannot create relationship link');
    } finally {
      setSavingLink(false);
    }
  };

  const submitDeleteLinkForm = async (values: LinkFormValues) => {
    if (!currentTree) return;
    setSavingLink(true);
    try {
      await deleteLink(currentTree.id, {
        type: values.type,
        from_id: values.fromId,
        to_id: values.toId,
        side: values.type === 'parent_of' ? values.side : undefined,
      });
      deleteLinkForm.resetFields(['fromId', 'toId']);
      await reloadCurrentTree();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Cannot delete relationship link');
    } finally {
      setSavingLink(false);
    }
  };

  const openJsonViewer = () => {
    if (!currentTree) return;
    setJsonDraft(JSON.stringify(currentTree, null, 2));
    setJsonViewerOpen(true);
  };

  const openJsonEditor = () => {
    if (!currentTree) return;
    setJsonDraft(JSON.stringify(currentTree, null, 2));
    setJsonEditorOpen(true);
  };

  const openCrawlModal = () => {
    crawlForm.setFieldsValue({
      startId: 100,
      endId: 200,
      delaySeconds: 0.2,
      syncDb: true,
    });
    setCrawlModalOpen(true);
  };

  const submitCrawlForm = async (values: CrawlFormValues) => {
    setCrawlingData(true);
    setPageError(null);
    try {
      await crawlAndSyncVietnamGiaPha({
        start_id: values.startId,
        end_id: values.endId,
        delay_seconds: values.delaySeconds,
        sync_db: values.syncDb,
      });
      setCrawlModalOpen(false);
      await loadTrees(drawerOpen ? selectedTreeId ?? undefined : undefined);
      if (drawerOpen && selectedTreeId) {
        await openTreeDetail(selectedTreeId);
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Không thể crawl/sync dữ liệu');
    } finally {
      setCrawlingData(false);
    }
  };

  const submitJsonEditor = async () => {
    if (!currentTree) return;

    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonDraft);
    } catch {
      setPageError('JSON không hợp lệ: vui lòng kiểm tra cú pháp.');
      return;
    }

    if (!parsed || typeof parsed !== 'object') {
      setPageError('JSON phải là object document của cây gia phả.');
      return;
    }

    const doc = parsed as {
      name?: unknown;
      description?: unknown;
      nodes?: unknown;
    };

    if (typeof doc.name !== 'string' || !doc.name.trim()) {
      setPageError('JSON thiếu trường name hợp lệ.');
      return;
    }
    if (!Array.isArray(doc.nodes)) {
      setPageError('JSON thiếu trường nodes dạng mảng.');
      return;
    }

    setSavingJson(true);
    try {
      const safeName = doc.name as string;
      const safeDescription: string | null =
        typeof doc.description === 'string' ? doc.description : null;
      const updated = await replaceFamilyTreeDocument(currentTree.id, {
        name: safeName,
        description: safeDescription,
        nodes: doc.nodes as BalkanNode[],
      });
      setCurrentTree(updated);
      setJsonEditorOpen(false);
      await loadTrees(updated.id);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Không thể lưu JSON');
    } finally {
      setSavingJson(false);
    }
  };

  const filteredTrees = useMemo(() => {
    const kw = treeSearchKeyword.trim().toLowerCase();
    if (!kw) return trees;
    return trees.filter((tree) => {
      const name = (tree.name ?? '').toLowerCase();
      const id = (tree.id ?? '').toLowerCase();
      const description = (tree.description ?? '').toLowerCase();
      return name.includes(kw) || id.includes(kw) || description.includes(kw);
    });
  }, [trees, treeSearchKeyword]);

  const formatTreeDate = (value: string) => {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString('vi-VN');
  };

  const ancestorOptions = currentTree?.nodes.map((node) => ({ label: `${node.name} (#${node.id})`, value: Number(node.id) })) ?? [];
  const spouseOptions = ancestorOptions;

  const treeDetailContent = currentTree ? (
    <>
      <Descriptions
        bordered
        size="small"
        className="mb-4"
        title={t('familyTree.treeDetailTitle', { defaultValue: 'Chi tiết cây gia phả' })}
        column={{ xs: 1, sm: 2 }}
      >
        <Descriptions.Item label="ID">{currentTree.id}</Descriptions.Item>
        <Descriptions.Item label={t('familyTree.treeName', { defaultValue: 'Tên cây' })}>
          {currentTree.name}
        </Descriptions.Item>
        <Descriptions.Item label={t('familyTree.totalMembers', { defaultValue: 'Tổng thành viên' })}>
          {stats.totalMembers}
        </Descriptions.Item>
        <Descriptions.Item label={t('familyTree.totalGenerations', { defaultValue: 'Tổng thế hệ' })}>
          {Math.max(1, members.reduce((max, member) => Math.max(max, member.generation), 1))}
        </Descriptions.Item>
        <Descriptions.Item label={t('familyTree.createdAt', { defaultValue: 'Ngày tạo' })}>
          {new Date(currentTree.created_at).toLocaleString('vi-VN')}
        </Descriptions.Item>
        <Descriptions.Item label={t('familyTree.updatedAt', { defaultValue: 'Cập nhật' })}>
          {new Date(currentTree.updated_at).toLocaleString('vi-VN')}
        </Descriptions.Item>
        <Descriptions.Item label={t('familyTree.treeDescription', { defaultValue: 'Mô tả' })} span={2}>
          {currentTree.description || t('familyTree.noDescription', { defaultValue: 'Không có mô tả' })}
        </Descriptions.Item>
      </Descriptions>

      <Tabs
        defaultActiveKey="visual"
        items={[
          {
            key: 'visual',
            label: t('familyTree.visualTreeTitle', { defaultValue: 'Cây gia phả trực quan' }),
            children:
              currentTree.nodes.length > 0 ? (
                <BalkanFamilyTreeView
                  key={currentTree.id}
                  treeId={currentTree.id}
                  nodes={currentTree.nodes}
                  height={520}
                />
              ) : (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={t('familyTree.emptyTree', { defaultValue: 'Cây này chưa có node nào' })}
                />
              ),
          },
          {
            key: 'members',
            label: t('familyTree.memberGridTitle', { defaultValue: 'Danh sách thành viên' }),
            children: (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {members.map((member) => (
                  <FamilyTreeNode
                    key={member.id}
                    member={member}
                    onSelect={() => setSelectedNodeId(Number(member.id))}
                    isSelected={selectedNodeId === Number(member.id)}
                  />
                ))}
              </div>
            ),
          },
          {
            key: 'links',
            label: t('familyTree.relationshipManager', { defaultValue: 'Quản lý liên kết quan hệ' }),
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24}>
                  <Card size="small" title={t('familyTree.createLink', { defaultValue: 'Tạo liên kết' })}>
                    <Form
                      form={createLinkForm}
                      layout="vertical"
                      initialValues={{ type: 'spouse_of', side: 'fid' }}
                      onFinish={submitCreateLinkForm}
                    >
                      <Row gutter={12}>
                        <Col span={12}>
                          <Form.Item label={t('familyTree.linkType', { defaultValue: 'Loại quan hệ' })} name="type" rules={[{ required: true }]}>
                            <Select
                              options={[
                                { value: 'spouse_of', label: t('familyTree.spouseLink', { defaultValue: 'Vợ / chồng' }) },
                                { value: 'parent_of', label: t('familyTree.parentLink', { defaultValue: 'Cha/mẹ -> con' }) },
                              ]}
                            />
                          </Form.Item>
                        </Col>
                        <Col span={12}>
                          <Form.Item noStyle shouldUpdate>
                            {({ getFieldValue }) =>
                              getFieldValue('type') === 'parent_of' ? (
                                <Form.Item label={t('familyTree.parentSide', { defaultValue: 'Vai trò cha/mẹ' })} name="side" rules={[{ required: true }]}>
                                  <Select
                                    options={[
                                      { value: 'fid', label: t('familyTree.father', { defaultValue: 'Cha (fid)' }) },
                                      { value: 'mid', label: t('familyTree.mother', { defaultValue: 'Mẹ (mid)' }) },
                                    ]}
                                  />
                                </Form.Item>
                              ) : null
                            }
                          </Form.Item>
                        </Col>
                      </Row>
                      <Form.Item label={t('familyTree.fromNode', { defaultValue: 'Từ node' })} name="fromId" rules={[{ required: true }]}>
                        <Select options={ancestorOptions} />
                      </Form.Item>
                      <Form.Item label={t('familyTree.toNode', { defaultValue: 'Đến node' })} name="toId" rules={[{ required: true }]}>
                        <Select options={ancestorOptions} />
                      </Form.Item>
                      <Button htmlType="submit" type="primary" loading={savingLink}>
                        {t('familyTree.createLink', { defaultValue: 'Tạo liên kết' })}
                      </Button>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24}>
                  <Card size="small" title={t('familyTree.deleteLink', { defaultValue: 'Gỡ liên kết' })}>
                    <Form
                      form={deleteLinkForm}
                      layout="vertical"
                      initialValues={{ type: 'spouse_of', side: 'fid' }}
                      onFinish={submitDeleteLinkForm}
                    >
                      <Row gutter={12}>
                        <Col span={12}>
                          <Form.Item label={t('familyTree.linkType', { defaultValue: 'Loại quan hệ' })} name="type" rules={[{ required: true }]}>
                            <Select
                              options={[
                                { value: 'spouse_of', label: t('familyTree.spouseLink', { defaultValue: 'Vợ / chồng' }) },
                                { value: 'parent_of', label: t('familyTree.parentLink', { defaultValue: 'Cha/mẹ -> con' }) },
                              ]}
                            />
                          </Form.Item>
                        </Col>
                        <Col span={12}>
                          <Form.Item noStyle shouldUpdate>
                            {({ getFieldValue }) =>
                              getFieldValue('type') === 'parent_of' ? (
                                <Form.Item label={t('familyTree.parentSide', { defaultValue: 'Vai trò cha/mẹ' })} name="side">
                                  <Select
                                    allowClear
                                    options={[
                                      { value: 'fid', label: t('familyTree.father', { defaultValue: 'Cha (fid)' }) },
                                      { value: 'mid', label: t('familyTree.mother', { defaultValue: 'Mẹ (mid)' }) },
                                    ]}
                                  />
                                </Form.Item>
                              ) : null
                            }
                          </Form.Item>
                        </Col>
                      </Row>
                      <Form.Item label={t('familyTree.fromNode', { defaultValue: 'Từ node' })} name="fromId" rules={[{ required: true }]}>
                        <Select options={ancestorOptions} />
                      </Form.Item>
                      <Form.Item label={t('familyTree.toNode', { defaultValue: 'Đến node' })} name="toId" rules={[{ required: true }]}>
                        <Select options={ancestorOptions} />
                      </Form.Item>
                      <Button htmlType="submit" danger loading={savingLink}>
                        {t('familyTree.deleteLink', { defaultValue: 'Gỡ liên kết' })}
                      </Button>
                    </Form>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'documents',
            label: t('familyTree.documentsTab', { defaultValue: 'Tài liệu' }),
            children: <FamilyTreeDocumentsPanel treeId={currentTree.id} />,
          },
        ]}
      />
    </>
  ) : null;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Typography.Paragraph type="secondary" className="!mb-0">
          {t('familyTree.managerSubtitle', {
            defaultValue: 'Quản lý danh sách cây gia phả. Bấm Chi tiết để xem và chỉnh sửa.',
          })}
        </Typography.Paragraph>
        <div className="flex flex-wrap items-center gap-3">
          <Button icon={<CloudDownloadOutlined />} onClick={openCrawlModal} loading={crawlingData}>
            {t('familyTree.crawlSync', { defaultValue: 'Crawl + Sync DB' })}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => loadTrees()} loading={loadingTrees}>
            {t('familyTree.reload', { defaultValue: 'Tải lại' })}
          </Button>
          <Button icon={<PlusOutlined />} onClick={openCreateTreeModal} type="primary">
            {t('familyTree.createTree', { defaultValue: 'Tạo cây mới' })}
          </Button>
        </div>
      </div>

      {pageError && (
        <Alert
          type="warning"
          showIcon
          className="mb-6"
          message={t('familyTree.errorTitle', { defaultValue: 'Không tải được dữ liệu' })}
          description={pageError}
        />
      )}

      <Card
        title={t('familyTree.treeListTitle', { defaultValue: 'Danh sách gia phả' })}
        extra={<Tag>{filteredTrees.length}</Tag>}
      >
        <Input.Search
          allowClear
          value={treeSearchKeyword}
          onChange={(event) => setTreeSearchKeyword(event.target.value)}
          placeholder={t('familyTree.searchTrees', { defaultValue: 'Tìm cây theo tên, mã hoặc mô tả' })}
          className="mb-4 max-w-md"
        />

        <Table
          rowKey="id"
          loading={loadingTrees}
          dataSource={filteredTrees}
          pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ['10', '20', '50'] }}
          scroll={{ x: 900 }}
          locale={{
            emptyText: (
              <Empty description={t('familyTree.noTrees', { defaultValue: 'Chưa có cây nào' })} image={Empty.PRESENTED_IMAGE_SIMPLE}>
                <Button type="primary" onClick={openCreateTreeModal}>
                  {t('familyTree.createTree', { defaultValue: 'Tạo cây mới' })}
                </Button>
              </Empty>
            ),
          }}
          columns={[
            {
              title: t('familyTree.treeName', { defaultValue: 'Gia phả' }).toUpperCase(),
              dataIndex: 'name',
              render: (_name: string, record: FamilyTreeSummary) => (
                <div className="flex items-center gap-3 min-w-[220px]">
                  <Avatar
                    size={40}
                    className="!bg-[#1677ff]/10 !text-[#1677ff] shrink-0"
                    icon={<BranchesOutlined />}
                  />
                  <div>
                    <div className="font-semibold text-foreground">{record.name}</div>
                    <div className="text-xs text-muted-foreground">{record.id}</div>
                  </div>
                </div>
              ),
            },
            {
              title: t('familyTree.treeDescription', { defaultValue: 'Mô tả' }).toUpperCase(),
              dataIndex: 'description',
              ellipsis: true,
              render: (description: string | null | undefined) =>
                description?.trim() || t('familyTree.noDescription', { defaultValue: 'Không có mô tả' }),
            },
            {
              title: t('familyTree.totalMembers', { defaultValue: 'Thành viên' }).toUpperCase(),
              dataIndex: 'node_count',
              width: 130,
              render: (count: number) => (
                <Tag color={count > 0 ? 'blue' : 'default'}>
                  {count} {t('familyTree.membersShort', { defaultValue: 'người' })}
                </Tag>
              ),
            },
            {
              title: t('familyTree.updatedAt', { defaultValue: 'Cập nhật' }).toUpperCase(),
              dataIndex: 'updated_at',
              width: 130,
              render: (value: string) => formatTreeDate(value),
            },
            {
              title: '',
              key: 'actions',
              width: 100,
              align: 'right',
              render: (_: unknown, record: FamilyTreeSummary) => (
                <Button type="link" className="!px-0" onClick={() => void openTreeDetail(record.id)}>
                  {t('familyTree.detail', { defaultValue: 'Chi tiết' })}
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Drawer
        title={currentTree?.name ?? t('familyTree.treeDetailTitle', { defaultValue: 'Chi tiết cây gia phả' })}
        placement="right"
        width={960}
        open={drawerOpen}
        onClose={closeTreeDrawer}
        destroyOnClose
        extra={
          currentTree ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button size="small" icon={<EditOutlined />} onClick={openEditTreeModal}>
                {t('familyTree.editTree', { defaultValue: 'Sửa' })}
              </Button>
              <Button size="small" icon={<DeleteOutlined />} danger onClick={handleDeleteTree}>
                {t('familyTree.deleteTree', { defaultValue: 'Xóa' })}
              </Button>
              <Button size="small" onClick={openJsonViewer}>
                {t('familyTree.viewJson', { defaultValue: 'JSON' })}
              </Button>
              <Button size="small" onClick={openJsonEditor}>
                {t('familyTree.editJson', { defaultValue: 'Sửa JSON' })}
              </Button>
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={openCreateMemberModal}>
                {t('familyTree.addMember', { defaultValue: 'Thêm' })}
              </Button>
            </div>
          ) : null
        }
      >
        {loadingTree ? (
          <div className="py-16 flex justify-center">
            <Spin size="large" tip={t('familyTree.loadingTreeDetail', { defaultValue: 'Đang tải chi tiết cây...' })} />
          </div>
        ) : currentTree ? (
          treeDetailContent
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={t('familyTree.treeDetailLoadFailed', { defaultValue: 'Không tải được chi tiết cây' })}
          >
            {selectedTreeId && (
              <Button onClick={() => void openTreeDetail(selectedTreeId)}>
                {t('familyTree.reload', { defaultValue: 'Tải lại' })}
              </Button>
            )}
          </Empty>
        )}
      </Drawer>

      <Modal
        open={treeModalOpen}
        onCancel={() => {
          setTreeModalOpen(false);
          setEditingTree(null);
        }}
        title={editingTree ? t('familyTree.editTreeTitle', { defaultValue: 'Sửa cây gia phả' }) : t('familyTree.createTreeTitle', { defaultValue: 'Tạo cây gia phả' })}
        footer={null}
        destroyOnClose
      >
        <Form form={treeForm} layout="vertical" onFinish={submitTreeForm}>
          <Form.Item
            label={t('familyTree.treeName', { defaultValue: 'Tên cây' })}
            name="name"
            rules={[{ required: true, message: t('familyTree.validationName', { defaultValue: 'Vui lòng nhập tên cây' }) }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label={t('familyTree.treeDescription', { defaultValue: 'Mô tả' })} name="description">
            <Input.TextArea rows={4} />
          </Form.Item>
          <div className="flex justify-end gap-3">
            <Button onClick={() => setTreeModalOpen(false)}>{t('familyTree.cancel', { defaultValue: 'Hủy' })}</Button>
            <Button type="primary" htmlType="submit" loading={savingTree}>
              {editingTree ? t('familyTree.save', { defaultValue: 'Lưu thay đổi' }) : t('familyTree.create', { defaultValue: 'Tạo mới' })}
            </Button>
          </div>
        </Form>
      </Modal>

      <Modal
        open={memberModalOpen}
        onCancel={() => {
          setMemberModalOpen(false);
          setEditingNode(null);
        }}
        title={editingNode ? t('familyTree.editMember', { defaultValue: 'Sửa thành viên' }) : t('familyTree.addMember', { defaultValue: 'Thêm thành viên' })}
        footer={null}
        width={720}
        destroyOnClose
      >
        <Form form={memberForm} layout="vertical" onFinish={submitMemberForm}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={t('familyTree.fullName', { defaultValue: 'Họ và tên' })}
                name="name"
                rules={[{ required: true, message: t('familyTree.validationName', { defaultValue: 'Vui lòng nhập họ tên' }) }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label={t('familyTree.gender', { defaultValue: 'Giới tính' })}
                name="gender"
                rules={[{ required: true, message: t('familyTree.validationGender', { defaultValue: 'Vui lòng chọn giới tính' }) }]}
              >
                <Radio.Group>
                  <Radio value="male">{t('familyTree.male', { defaultValue: 'Nam' })}</Radio>
                  <Radio value="female">{t('familyTree.female', { defaultValue: 'Nữ' })}</Radio>
                </Radio.Group>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label={t('familyTree.birthYear', { defaultValue: 'Năm sinh' })} name="birthYear">
                <InputNumber className="w-full" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={t('familyTree.deathYear', { defaultValue: 'Năm mất' })} name="deathYear">
                <InputNumber className="w-full" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={t('familyTree.titleField', { defaultValue: 'Danh xưng / chức vụ' })} name="title">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label={t('familyTree.bio', { defaultValue: 'Tiểu sử' })} name="bio">
            <Input.TextArea rows={3} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label={t('familyTree.father', { defaultValue: 'Cha' })} name="fatherId">
                <Select allowClear options={ancestorOptions.filter((option) => !editingNode || option.value !== Number(editingNode.id))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label={t('familyTree.mother', { defaultValue: 'Mẹ' })} name="motherId">
                <Select allowClear options={ancestorOptions.filter((option) => !editingNode || option.value !== Number(editingNode.id))} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label={t('familyTree.spouseIds', { defaultValue: 'Vợ / chồng' })} name="spouseIds">
            <Select
              mode="multiple"
              allowClear
              options={spouseOptions.filter((option) => !editingNode || option.value !== Number(editingNode.id))}
            />
          </Form.Item>

          <div className="flex justify-between gap-3 pt-2">
            <div>
              {editingNode && currentTree && (
                <Button danger icon={<DeleteOutlined />} onClick={() => handleDeleteMember(editingNode)}>
                  {t('familyTree.deleteMember', { defaultValue: 'Xóa thành viên' })}
                </Button>
              )}
            </div>
            <div className="flex gap-3">
              <Button onClick={() => setMemberModalOpen(false)}>{t('familyTree.cancel', { defaultValue: 'Hủy' })}</Button>
              <Button type="primary" htmlType="submit" loading={savingNode}>
                {editingNode ? t('familyTree.save', { defaultValue: 'Lưu thay đổi' }) : t('familyTree.createMember', { defaultValue: 'Tạo thành viên' })}
              </Button>
            </div>
          </div>
        </Form>
      </Modal>

      <Modal
        open={jsonViewerOpen}
        onCancel={() => setJsonViewerOpen(false)}
        title={t('familyTree.viewJson', { defaultValue: 'Xem JSON' })}
        footer={[
          <Button key="close" onClick={() => setJsonViewerOpen(false)}>
            {t('familyTree.close', { defaultValue: 'Đóng' })}
          </Button>,
        ]}
        width={900}
        destroyOnClose
      >
        <Input.TextArea value={jsonDraft} readOnly autoSize={{ minRows: 18, maxRows: 28 }} />
      </Modal>

      <Modal
        open={jsonEditorOpen}
        onCancel={() => setJsonEditorOpen(false)}
        title={t('familyTree.editJson', { defaultValue: 'Sửa JSON trực tiếp' })}
        footer={[
          <Button key="cancel" onClick={() => setJsonEditorOpen(false)}>
            {t('familyTree.cancel', { defaultValue: 'Hủy' })}
          </Button>,
          <Button key="save" type="primary" loading={savingJson} onClick={submitJsonEditor}>
            {t('familyTree.save', { defaultValue: 'Lưu thay đổi' })}
          </Button>,
        ]}
        width={900}
        destroyOnClose
      >
        <Alert
          type="info"
          showIcon
          className="mb-3"
          message={t('familyTree.editJsonHint', {
            defaultValue: 'Sửa trực tiếp name/description/nodes. id, created_at và updated_at sẽ do backend quản lý.',
          })}
        />
        <Input.TextArea
          value={jsonDraft}
          onChange={(event) => setJsonDraft(event.target.value)}
          autoSize={{ minRows: 18, maxRows: 28 }}
        />
      </Modal>

      <Modal
        open={crawlModalOpen}
        onCancel={() => setCrawlModalOpen(false)}
        title={t('familyTree.crawlSyncTitle', { defaultValue: 'Crawl dữ liệu và đồng bộ database' })}
        footer={[
          <Button key="cancel" onClick={() => setCrawlModalOpen(false)}>
            {t('familyTree.cancel', { defaultValue: 'Hủy' })}
          </Button>,
          <Button key="run" type="primary" loading={crawlingData} onClick={() => crawlForm.submit()}>
            {t('familyTree.run', { defaultValue: 'Chạy' })}
          </Button>,
        ]}
        destroyOnClose
      >
        <Form form={crawlForm} layout="vertical" onFinish={submitCrawlForm}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label={t('familyTree.startId', { defaultValue: 'ID bắt đầu' })}
                name="startId"
                rules={[{ required: true, message: 'Nhập ID bắt đầu' }]}
              >
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label={t('familyTree.endId', { defaultValue: 'ID kết thúc' })}
                name="endId"
                rules={[{ required: true, message: 'Nhập ID kết thúc' }]}
              >
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label={t('familyTree.delaySeconds', { defaultValue: 'Delay giữa request (giây)' })}
            name="delaySeconds"
          >
            <InputNumber min={0} max={5} step={0.1} className="w-full" />
          </Form.Item>

          <Form.Item
            label={t('familyTree.syncDb', { defaultValue: 'Đồng bộ database' })}
            name="syncDb"
          >
            <Radio.Group>
              <Radio value>{t('common.yes', { defaultValue: 'Có' })}</Radio>
              <Radio value={false}>{t('common.no', { defaultValue: 'Không' })}</Radio>
            </Radio.Group>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={!!selectedNode}
        onCancel={() => setSelectedNodeId(null)}
        title={selectedMember?.name ?? t('familyTree.memberDetails', { defaultValue: 'Chi tiết thành viên' })}
        footer={selectedNode ? [
          <Button key="close" onClick={() => setSelectedNodeId(null)}>{t('familyTree.close', { defaultValue: 'Đóng' })}</Button>,
          <Button key="edit" type="primary" onClick={() => openEditMemberModal(selectedNode)}>{t('familyTree.editMember', { defaultValue: 'Sửa thành viên' })}</Button>,
        ] : null}
      >
        {selectedNode && selectedMember && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label={t('familyTree.fullName', { defaultValue: 'Họ và tên' })}>{selectedMember.name}</Descriptions.Item>
              <Descriptions.Item label={t('familyTree.birthYear', { defaultValue: 'Năm sinh' })}>{selectedMember.birthYear || '-'}</Descriptions.Item>
              <Descriptions.Item label={t('familyTree.deathYear', { defaultValue: 'Năm mất' })}>{selectedMember.deathYear ?? '-'}</Descriptions.Item>
              <Descriptions.Item label={t('familyTree.gender', { defaultValue: 'Giới tính' })}>{selectedMember.gender}</Descriptions.Item>
              <Descriptions.Item label={t('familyTree.generation', { defaultValue: 'Đời thứ' })}>{selectedMember.generation}</Descriptions.Item>
              <Descriptions.Item label={t('familyTree.father', { defaultValue: 'Cha' })}>{selectedNode.fid ?? '-'}</Descriptions.Item>
              <Descriptions.Item label={t('familyTree.mother', { defaultValue: 'Mẹ' })}>{selectedNode.mid ?? '-'}</Descriptions.Item>
              <Descriptions.Item label={t('familyTree.spouseIds', { defaultValue: 'Vợ / chồng' })}>{Array.isArray(selectedNode.pids) ? selectedNode.pids.join(', ') : '-'}</Descriptions.Item>
            </Descriptions>
            {(selectedMember.title || selectedMember.bio) && <Divider />}
            {selectedMember.title && <Tag color="gold">{selectedMember.title}</Tag>}
            {selectedMember.bio && <p className="mt-3 text-sm text-muted-foreground">{selectedMember.bio}</p>}
          </>
        )}
      </Modal>
    </div>
  );
};

export default FamilyTreeManagerPage;
