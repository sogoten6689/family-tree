import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Tabs,
  Tag,
  Typography,
} from "antd";
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { DeleteFamilyTreeModal } from "@/components/family-tree/DeleteFamilyTreeModal";
import { FamilyTreeVisualPanel } from "@/components/family-tree/FamilyTreeVisualPanel";
import { FamilyTreeAncestralSidebar } from "@/components/family-tree/FamilyTreeAncestralSidebar";
import { FamilyTreeMembersTable } from "@/components/family-tree/FamilyTreeMembersTable";
import { GenealogyPipelineSteps } from "@/components/pipeline/GenealogyPipelineSteps";
import { FamilyTreeDocumentsPanel } from "@/components/documents/FamilyTreeDocumentsPanel";
import { listTreeDocuments } from "@/lib/documentApi";
import {
  createLink,
  createNode,
  deleteFamilyTree,
  deleteLink,
  getFamilyTree,
  removeNode,
  replaceFamilyTreeDocument,
  updateFamilyTree,
  updateNode,
  type BalkanNode,
  type FamilyTreeDocument,
  type Gender,
} from "@/lib/familyTreeApi";
import { normalizeGender, toFamilyMembers, toTreeStats } from "@/lib/familyTreeUtils";

type TreeFormValues = { name: string; description?: string };
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
  type: "spouse_of" | "parent_of";
  fromId: number;
  toId: number;
  side?: "fid" | "mid";
};

const FamilyTreeDetailPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { treeId } = useParams<{ treeId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const activeTab = searchParams.get("tab") ?? "visual";

  const [tree, setTree] = useState<FamilyTreeDocument | null>(null);
  const [docCount, setDocCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [treeModalOpen, setTreeModalOpen] = useState(false);
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<BalkanNode | null>(null);
  const [savingTree, setSavingTree] = useState(false);
  const [savingNode, setSavingNode] = useState(false);
  const [savingLink, setSavingLink] = useState(false);
  const [jsonViewerOpen, setJsonViewerOpen] = useState(false);
  const [jsonEditorOpen, setJsonEditorOpen] = useState(false);
  const [savingJson, setSavingJson] = useState(false);
  const [jsonDraft, setJsonDraft] = useState("");
  const [deleteTreeOpen, setDeleteTreeOpen] = useState(false);
  const [deletingTree, setDeletingTree] = useState(false);

  const [treeForm] = Form.useForm<TreeFormValues>();
  const [memberForm] = Form.useForm<MemberFormValues>();
  const [createLinkForm] = Form.useForm<LinkFormValues>();
  const [deleteLinkForm] = Form.useForm<LinkFormValues>();

  const members = useMemo(() => toFamilyMembers(tree?.nodes ?? []), [tree]);
  const stats = useMemo(() => toTreeStats(tree?.nodes ?? []), [tree]);
  const selectedMember = useMemo(
    () => members.find((member) => Number(member.id) === selectedNodeId) ?? null,
    [members, selectedNodeId],
  );
  const selectedNode = useMemo(
    () => tree?.nodes.find((node) => Number(node.id) === selectedNodeId) ?? null,
    [tree, selectedNodeId],
  );

  const loadTree = async () => {
    if (!treeId) return;
    setLoading(true);
    setPageError(null);
    try {
      const [treeData, docsResponse] = await Promise.all([
        getFamilyTree(treeId),
        listTreeDocuments(treeId),
      ]);
      setTree(treeData);
      setDocCount(docsResponse.total ?? docsResponse.items.length);
    } catch (error) {
      setTree(null);
      setPageError(error instanceof Error ? error.message : "Không tải được chi tiết cây");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTree();
  }, [treeId]);

  const handleTabChange = (key: string) => {
    setSearchParams(key === "visual" ? {} : { tab: key }, { replace: true });
  };

  const openEditTreeModal = () => {
    if (!tree) return;
    treeForm.setFieldsValue({ name: tree.name, description: tree.description ?? "" });
    setTreeModalOpen(true);
  };

  const submitTreeForm = async (values: TreeFormValues) => {
    if (!tree) return;
    setSavingTree(true);
    try {
      const updated = await updateFamilyTree(tree.id, values);
      setTree(updated);
      setTreeModalOpen(false);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể lưu cây");
    } finally {
      setSavingTree(false);
    }
  };

  const handleDeleteTree = async () => {
    if (!tree) return;
    setDeletingTree(true);
    try {
      await deleteFamilyTree(tree.id);
      navigate("/admin/gia-pha");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể xóa cây");
    } finally {
      setDeletingTree(false);
      setDeleteTreeOpen(false);
    }
  };

  const reloadTree = async () => {
    if (!treeId) return;
    try {
      const updated = await getFamilyTree(treeId);
      setTree(updated);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể tải lại cây");
    }
  };

  const openCreateMemberModal = () => {
    setEditingNode(null);
    memberForm.resetFields();
    memberForm.setFieldsValue({ gender: "male", spouseIds: [] });
    setMemberModalOpen(true);
  };

  const openEditMemberModal = (node: BalkanNode) => {
    setEditingNode(node);
    memberForm.setFieldsValue({
      name: node.name,
      gender: normalizeGender(node.gender, node.name),
      birthYear: node.birthYear,
      deathYear: node.deathYear,
      title: typeof node.title === "string" ? node.title : undefined,
      bio: typeof node.bio === "string" ? node.bio : undefined,
      fatherId: node.fid,
      motherId: node.mid,
      spouseIds: Array.isArray(node.pids) ? node.pids : [],
    });
    setMemberModalOpen(true);
  };

  const submitMemberForm = async (values: MemberFormValues) => {
    if (!tree) return;
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
        await updateNode(tree.id, Number(editingNode.id), payload);
      } else {
        await createNode(tree.id, payload);
      }

      setMemberModalOpen(false);
      setEditingNode(null);
      await reloadTree();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể lưu thành viên");
    } finally {
      setSavingNode(false);
    }
  };

  const handleDeleteMember = (node: BalkanNode) => {
    if (!tree) return;
    Modal.confirm({
      title: t("familyTree.deleteMemberTitle", { defaultValue: "Xóa thành viên" }),
      content: t("familyTree.deleteMemberConfirm", {
        defaultValue: "Xóa thành viên này sẽ đồng thời dọn các liên kết quan hệ liên quan.",
      }),
      okText: t("familyTree.delete", { defaultValue: "Xóa" }),
      okButtonProps: { danger: true },
      cancelText: t("familyTree.cancel", { defaultValue: "Hủy" }),
      onOk: async () => {
        await removeNode(tree.id, Number(node.id));
        setSelectedNodeId((prev) => (prev === Number(node.id) ? null : prev));
        await reloadTree();
      },
    });
  };

  const submitCreateLinkForm = async (values: LinkFormValues) => {
    if (!tree) return;
    setSavingLink(true);
    try {
      await createLink(tree.id, {
        type: values.type,
        from_id: values.fromId,
        to_id: values.toId,
        side: values.type === "parent_of" ? values.side : undefined,
      });
      createLinkForm.resetFields(["fromId", "toId"]);
      await reloadTree();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể tạo liên kết");
    } finally {
      setSavingLink(false);
    }
  };

  const submitDeleteLinkForm = async (values: LinkFormValues) => {
    if (!tree) return;
    setSavingLink(true);
    try {
      await deleteLink(tree.id, {
        type: values.type,
        from_id: values.fromId,
        to_id: values.toId,
        side: values.type === "parent_of" ? values.side : undefined,
      });
      deleteLinkForm.resetFields(["fromId", "toId"]);
      await reloadTree();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể gỡ liên kết");
    } finally {
      setSavingLink(false);
    }
  };

  const openJsonViewer = () => {
    if (!tree) return;
    setJsonDraft(JSON.stringify(tree, null, 2));
    setJsonViewerOpen(true);
  };

  const openJsonEditor = () => {
    if (!tree) return;
    setJsonDraft(JSON.stringify(tree, null, 2));
    setJsonEditorOpen(true);
  };

  const submitJsonEditor = async () => {
    if (!tree) return;

    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonDraft);
    } catch {
      setPageError("JSON không hợp lệ: vui lòng kiểm tra cú pháp.");
      return;
    }

    if (!parsed || typeof parsed !== "object") {
      setPageError("JSON phải là object document của cây gia phả.");
      return;
    }

    const doc = parsed as { name?: unknown; description?: unknown; nodes?: unknown };
    if (typeof doc.name !== "string" || !doc.name.trim()) {
      setPageError("JSON thiếu trường name hợp lệ.");
      return;
    }
    if (!Array.isArray(doc.nodes)) {
      setPageError("JSON thiếu trường nodes dạng mảng.");
      return;
    }

    setSavingJson(true);
    try {
      const updated = await replaceFamilyTreeDocument(tree.id, {
        name: doc.name,
        description: typeof doc.description === "string" ? doc.description : undefined,
        nodes: doc.nodes as BalkanNode[],
      });
      setTree(updated);
      setJsonEditorOpen(false);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể lưu JSON");
    } finally {
      setSavingJson(false);
    }
  };

  const ancestorOptions =
    tree?.nodes.map((node) => ({ label: `${node.name} (#${node.id})`, value: Number(node.id) })) ?? [];

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Spin size="large" tip={t("familyTree.loadingTreeDetail", { defaultValue: "Đang tải chi tiết cây..." })} />
      </div>
    );
  }

  if (!tree) {
    return (
      <Empty description={t("familyTree.treeDetailLoadFailed", { defaultValue: "Không tải được chi tiết cây" })}>
        <Button onClick={() => navigate("/admin/gia-pha")}>
          {t("familyTree.backToList", { defaultValue: "Quay lại danh sách" })}
        </Button>
      </Empty>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {pageError && (
        <Alert type="warning" showIcon className="mb-4" message={pageError} closable onClose={() => setPageError(null)} />
      )}

      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/admin/gia-pha")} className="mb-4">
        {t("familyTree.backToList", { defaultValue: "Quay lại danh sách" })}
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div>
          <Typography.Title level={2} className="!mb-2">
            {tree.name}
          </Typography.Title>
          <Space wrap>
            <Tag color="blue">{t("familyTree.statusPublic", { defaultValue: "Công khai" })}</Tag>
            <Typography.Text type="secondary">{tree.id}</Typography.Text>
          </Space>
        </div>
        <Space wrap>
          <Button icon={<EditOutlined />} onClick={openEditTreeModal}>
            {t("familyTree.editTree", { defaultValue: "Sửa" })}
          </Button>
          <Button icon={<FileTextOutlined />} onClick={() => handleTabChange("documents")}>
            {t("familyTree.documentsTab", { defaultValue: "Tài liệu" })}
          </Button>
          <Button onClick={openJsonViewer}>{t("familyTree.viewJson", { defaultValue: "JSON" })}</Button>
          <Button onClick={openJsonEditor}>{t("familyTree.editJson", { defaultValue: "Sửa JSON" })}</Button>
          <Button danger icon={<DeleteOutlined />} onClick={() => setDeleteTreeOpen(true)}>
            {t("familyTree.deleteTree", { defaultValue: "Xóa" })}
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateMemberModal}>
            {t("familyTree.addMember", { defaultValue: "Thêm" })}
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t("familyTree.totalMembers", { defaultValue: "Thành viên" })}
              value={stats.totalMembers}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t("familyTree.totalDocuments", { defaultValue: "Tổng tài liệu" })}
              value={docCount}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t("familyTree.totalGenerations", { defaultValue: "Số đời" })}
              value={stats.totalGenerations}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={17}>
          <Card>
            <Tabs
              activeKey={activeTab}
              onChange={handleTabChange}
              items={[
                {
                  key: "visual",
                  label: t("familyTree.visualTreeTab", { defaultValue: "Sơ đồ Gia phả" }),
                  children:
                    tree.nodes.length > 0 ? (
                      <FamilyTreeVisualPanel
                        key={tree.id}
                        nodes={tree.nodes}
                        treeName={tree.name}
                        members={members}
                        selectedMemberId={selectedNodeId}
                        onSelectMember={setSelectedNodeId}
                      />
                    ) : (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={t("familyTree.emptyTree", { defaultValue: "Cây này chưa có node nào" })}
                      />
                    ),
                },
                {
                  key: "members",
                  label: t("familyTree.memberDirectoryTab", { defaultValue: "Hồ sơ Thành viên" }),
                  children: (
                    <FamilyTreeMembersTable members={members} onSelectMember={setSelectedNodeId} />
                  ),
                },
                {
                  key: "pipeline",
                  label: t("pipeline.tab", { defaultValue: "Pipeline" }),
                  children: <GenealogyPipelineSteps treeId={tree.id} />,
                },
                {
                  key: "documents",
                  label: t("familyTree.documentArchiveTab", {
                    defaultValue: "Kho Tư liệu Hán-Nôm & Văn bản",
                  }),
                  children: <FamilyTreeDocumentsPanel treeId={tree.id} />,
                },
                {
                  key: "links",
                  label: t("familyTree.relationshipManager", { defaultValue: "Quản lý quan hệ" }),
                  children: (
                    <Row gutter={[16, 16]}>
                      <Col xs={24}>
                        <Card size="small" title={t("familyTree.createLink", { defaultValue: "Tạo liên kết" })}>
                          <Form
                            form={createLinkForm}
                            layout="vertical"
                            initialValues={{ type: "spouse_of", side: "fid" }}
                            onFinish={submitCreateLinkForm}
                          >
                            <Row gutter={12}>
                              <Col span={12}>
                                <Form.Item
                                  label={t("familyTree.linkType", { defaultValue: "Loại quan hệ" })}
                                  name="type"
                                  rules={[{ required: true }]}
                                >
                                  <Select
                                    options={[
                                      {
                                        value: "spouse_of",
                                        label: t("familyTree.spouseLink", { defaultValue: "Vợ / chồng" }),
                                      },
                                      {
                                        value: "parent_of",
                                        label: t("familyTree.parentLink", { defaultValue: "Cha/mẹ -> con" }),
                                      },
                                    ]}
                                  />
                                </Form.Item>
                              </Col>
                              <Col span={12}>
                                <Form.Item noStyle shouldUpdate>
                                  {({ getFieldValue }) =>
                                    getFieldValue("type") === "parent_of" ? (
                                      <Form.Item
                                        label={t("familyTree.parentSide", { defaultValue: "Vai trò cha/mẹ" })}
                                        name="side"
                                        rules={[{ required: true }]}
                                      >
                                        <Select
                                          options={[
                                            {
                                              value: "fid",
                                              label: t("familyTree.father", { defaultValue: "Cha (fid)" }),
                                            },
                                            {
                                              value: "mid",
                                              label: t("familyTree.mother", { defaultValue: "Mẹ (mid)" }),
                                            },
                                          ]}
                                        />
                                      </Form.Item>
                                    ) : null
                                  }
                                </Form.Item>
                              </Col>
                            </Row>
                            <Form.Item
                              label={t("familyTree.fromNode", { defaultValue: "Từ node" })}
                              name="fromId"
                              rules={[{ required: true }]}
                            >
                              <Select options={ancestorOptions} />
                            </Form.Item>
                            <Form.Item
                              label={t("familyTree.toNode", { defaultValue: "Đến node" })}
                              name="toId"
                              rules={[{ required: true }]}
                            >
                              <Select options={ancestorOptions} />
                            </Form.Item>
                            <Button htmlType="submit" type="primary" loading={savingLink}>
                              {t("familyTree.createLink", { defaultValue: "Tạo liên kết" })}
                            </Button>
                          </Form>
                        </Card>
                      </Col>
                      <Col xs={24}>
                        <Card size="small" title={t("familyTree.deleteLink", { defaultValue: "Gỡ liên kết" })}>
                          <Form
                            form={deleteLinkForm}
                            layout="vertical"
                            initialValues={{ type: "spouse_of", side: "fid" }}
                            onFinish={submitDeleteLinkForm}
                          >
                            <Row gutter={12}>
                              <Col span={12}>
                                <Form.Item
                                  label={t("familyTree.linkType", { defaultValue: "Loại quan hệ" })}
                                  name="type"
                                  rules={[{ required: true }]}
                                >
                                  <Select
                                    options={[
                                      {
                                        value: "spouse_of",
                                        label: t("familyTree.spouseLink", { defaultValue: "Vợ / chồng" }),
                                      },
                                      {
                                        value: "parent_of",
                                        label: t("familyTree.parentLink", { defaultValue: "Cha/mẹ -> con" }),
                                      },
                                    ]}
                                  />
                                </Form.Item>
                              </Col>
                              <Col span={12}>
                                <Form.Item noStyle shouldUpdate>
                                  {({ getFieldValue }) =>
                                    getFieldValue("type") === "parent_of" ? (
                                      <Form.Item
                                        label={t("familyTree.parentSide", { defaultValue: "Vai trò cha/mẹ" })}
                                        name="side"
                                      >
                                        <Select
                                          allowClear
                                          options={[
                                            {
                                              value: "fid",
                                              label: t("familyTree.father", { defaultValue: "Cha (fid)" }),
                                            },
                                            {
                                              value: "mid",
                                              label: t("familyTree.mother", { defaultValue: "Mẹ (mid)" }),
                                            },
                                          ]}
                                        />
                                      </Form.Item>
                                    ) : null
                                  }
                                </Form.Item>
                              </Col>
                            </Row>
                            <Form.Item
                              label={t("familyTree.fromNode", { defaultValue: "Từ node" })}
                              name="fromId"
                              rules={[{ required: true }]}
                            >
                              <Select options={ancestorOptions} />
                            </Form.Item>
                            <Form.Item
                              label={t("familyTree.toNode", { defaultValue: "Đến node" })}
                              name="toId"
                              rules={[{ required: true }]}
                            >
                              <Select options={ancestorOptions} />
                            </Form.Item>
                            <Button htmlType="submit" danger loading={savingLink}>
                              {t("familyTree.deleteLink", { defaultValue: "Gỡ liên kết" })}
                            </Button>
                          </Form>
                        </Card>
                      </Col>
                    </Row>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={7}>
          <FamilyTreeAncestralSidebar tree={tree} establishedYear={stats.established} />
        </Col>
      </Row>

      <Modal
        open={treeModalOpen}
        onCancel={() => setTreeModalOpen(false)}
        title={t("familyTree.editTreeTitle", { defaultValue: "Sửa cây gia phả" })}
        footer={null}
        destroyOnClose
      >
        <Form form={treeForm} layout="vertical" onFinish={submitTreeForm}>
          <Form.Item
            label={t("familyTree.treeName", { defaultValue: "Tên cây" })}
            name="name"
            rules={[{ required: true, message: t("familyTree.validationName", { defaultValue: "Vui lòng nhập tên cây" }) }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label={t("familyTree.treeDescription", { defaultValue: "Mô tả" })} name="description">
            <Input.TextArea rows={4} />
          </Form.Item>
          <div className="flex justify-end gap-3">
            <Button onClick={() => setTreeModalOpen(false)}>{t("familyTree.cancel", { defaultValue: "Hủy" })}</Button>
            <Button type="primary" htmlType="submit" loading={savingTree}>
              {t("familyTree.save", { defaultValue: "Lưu thay đổi" })}
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
        title={
          editingNode
            ? t("familyTree.editMember", { defaultValue: "Sửa thành viên" })
            : t("familyTree.addMember", { defaultValue: "Thêm thành viên" })
        }
        footer={null}
        width={720}
        destroyOnClose
      >
        <Form form={memberForm} layout="vertical" onFinish={submitMemberForm}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={t("familyTree.fullName", { defaultValue: "Họ và tên" })}
                name="name"
                rules={[{ required: true, message: t("familyTree.validationName", { defaultValue: "Vui lòng nhập họ tên" }) }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label={t("familyTree.gender", { defaultValue: "Giới tính" })}
                name="gender"
                rules={[{ required: true, message: t("familyTree.validationGender", { defaultValue: "Vui lòng chọn giới tính" }) }]}
              >
                <Radio.Group>
                  <Radio value="male">{t("familyTree.male", { defaultValue: "Nam" })}</Radio>
                  <Radio value="female">{t("familyTree.female", { defaultValue: "Nữ" })}</Radio>
                </Radio.Group>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label={t("familyTree.birthYear", { defaultValue: "Năm sinh" })} name="birthYear">
                <InputNumber className="w-full" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={t("familyTree.deathYear", { defaultValue: "Năm mất" })} name="deathYear">
                <InputNumber className="w-full" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={t("familyTree.titleField", { defaultValue: "Danh xưng / chức vụ" })} name="title">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t("familyTree.bio", { defaultValue: "Tiểu sử" })} name="bio">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label={t("familyTree.father", { defaultValue: "Cha" })} name="fatherId">
                <Select
                  allowClear
                  options={ancestorOptions.filter(
                    (option) => !editingNode || option.value !== Number(editingNode.id),
                  )}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label={t("familyTree.mother", { defaultValue: "Mẹ" })} name="motherId">
                <Select
                  allowClear
                  options={ancestorOptions.filter(
                    (option) => !editingNode || option.value !== Number(editingNode.id),
                  )}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t("familyTree.spouseIds", { defaultValue: "Vợ / chồng" })} name="spouseIds">
            <Select
              mode="multiple"
              allowClear
              options={ancestorOptions.filter(
                (option) => !editingNode || option.value !== Number(editingNode.id),
              )}
            />
          </Form.Item>
          <div className="flex justify-between gap-3 pt-2">
            <div>
              {editingNode && (
                <Button danger icon={<DeleteOutlined />} onClick={() => handleDeleteMember(editingNode)}>
                  {t("familyTree.deleteMember", { defaultValue: "Xóa thành viên" })}
                </Button>
              )}
            </div>
            <div className="flex gap-3">
              <Button onClick={() => setMemberModalOpen(false)}>{t("familyTree.cancel", { defaultValue: "Hủy" })}</Button>
              <Button type="primary" htmlType="submit" loading={savingNode}>
                {editingNode
                  ? t("familyTree.save", { defaultValue: "Lưu thay đổi" })
                  : t("familyTree.createMember", { defaultValue: "Tạo thành viên" })}
              </Button>
            </div>
          </div>
        </Form>
      </Modal>

      <Modal
        open={jsonViewerOpen}
        onCancel={() => setJsonViewerOpen(false)}
        title={t("familyTree.viewJson", { defaultValue: "Xem JSON" })}
        footer={[
          <Button key="close" onClick={() => setJsonViewerOpen(false)}>
            {t("familyTree.close", { defaultValue: "Đóng" })}
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
        title={t("familyTree.editJson", { defaultValue: "Sửa JSON trực tiếp" })}
        footer={[
          <Button key="cancel" onClick={() => setJsonEditorOpen(false)}>
            {t("familyTree.cancel", { defaultValue: "Hủy" })}
          </Button>,
          <Button key="save" type="primary" loading={savingJson} onClick={submitJsonEditor}>
            {t("familyTree.save", { defaultValue: "Lưu thay đổi" })}
          </Button>,
        ]}
        width={900}
        destroyOnClose
      >
        <Alert
          type="info"
          showIcon
          className="mb-3"
          message={t("familyTree.editJsonHint", {
            defaultValue: "Sửa trực tiếp name/description/nodes. id, created_at và updated_at sẽ do backend quản lý.",
          })}
        />
        <Input.TextArea
          value={jsonDraft}
          onChange={(event) => setJsonDraft(event.target.value)}
          autoSize={{ minRows: 18, maxRows: 28 }}
        />
      </Modal>

      <Modal
        open={!!selectedNode}
        onCancel={() => setSelectedNodeId(null)}
        title={selectedMember?.name ?? t("familyTree.memberDetails", { defaultValue: "Chi tiết thành viên" })}
        footer={
          selectedNode
            ? [
                <Button key="close" onClick={() => setSelectedNodeId(null)}>
                  {t("familyTree.close", { defaultValue: "Đóng" })}
                </Button>,
                <Button key="edit" type="primary" onClick={() => openEditMemberModal(selectedNode)}>
                  {t("familyTree.editMember", { defaultValue: "Sửa thành viên" })}
                </Button>,
              ]
            : null
        }
      >
        {selectedNode && selectedMember && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label={t("familyTree.fullName", { defaultValue: "Họ và tên" })}>
                {selectedMember.name}
              </Descriptions.Item>
              <Descriptions.Item label={t("familyTree.birthYear", { defaultValue: "Năm sinh" })}>
                {selectedMember.birthYear || "-"}
              </Descriptions.Item>
              <Descriptions.Item label={t("familyTree.deathYear", { defaultValue: "Năm mất" })}>
                {selectedMember.deathYear ?? "-"}
              </Descriptions.Item>
              <Descriptions.Item label={t("familyTree.gender", { defaultValue: "Giới tính" })}>
                {selectedMember.gender}
              </Descriptions.Item>
              <Descriptions.Item label={t("familyTree.generation", { defaultValue: "Đời thứ" })}>
                {selectedMember.generation}
              </Descriptions.Item>
            </Descriptions>
            {(selectedMember.title || selectedMember.bio) && <Divider />}
            {selectedMember.title && <Tag color="gold">{selectedMember.title}</Tag>}
            {selectedMember.bio && <p className="mt-3 text-sm text-muted-foreground">{selectedMember.bio}</p>}
          </>
        )}
      </Modal>

      {tree && (
        <DeleteFamilyTreeModal
          open={deleteTreeOpen}
          treeId={tree.id}
          treeName={tree.name}
          loading={deletingTree}
          onCancel={() => setDeleteTreeOpen(false)}
          onConfirm={handleDeleteTree}
        />
      )}
    </div>
  );
};

export default FamilyTreeDetailPage;
