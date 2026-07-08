import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Button,
  Card,
  Checkbox,
  Col,
  Empty,
  Form,
  Input,
  Modal,
  Row,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  BranchesOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  LinkOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  createFamilyTree,
  listFamilyTrees,
  updateFamilyTree,
  type FamilyTreeSummary,
} from "@/lib/familyTreeApi";
import { formatTreeDate, getFamilyTreeExternalUrl } from "@/lib/familyTreeUtils";

type TreeFormValues = {
  name: string;
  description?: string;
  external_url?: string;
  has_source_document?: boolean;
  has_hannom_text?: boolean;
  is_public?: boolean;
};

const FamilyTreeManagerPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [trees, setTrees] = useState<FamilyTreeSummary[]>([]);
  const [loadingTrees, setLoadingTrees] = useState(false);
  const [savingTree, setSavingTree] = useState(false);
  const [updatingFlagId, setUpdatingFlagId] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [treeModalOpen, setTreeModalOpen] = useState(false);
  const [editingTree, setEditingTree] = useState<FamilyTreeSummary | null>(null);
  const [treeSearchKeyword, setTreeSearchKeyword] = useState("");

  const [treeForm] = Form.useForm<TreeFormValues>();

  const loadTrees = async () => {
    setLoadingTrees(true);
    setPageError(null);
    try {
      const response = await listFamilyTrees();
      setTrees(response.items);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Cannot load trees");
      setTrees([]);
    } finally {
      setLoadingTrees(false);
    }
  };

  useEffect(() => {
    void loadTrees();
  }, []);

  const filteredTrees = useMemo(() => {
    const kw = treeSearchKeyword.trim().toLowerCase();
    if (!kw) return trees;
    return trees.filter((tree) => {
      const name = (tree.name ?? "").toLowerCase();
      const id = (tree.id ?? "").toLowerCase();
      const description = (tree.description ?? "").toLowerCase();
      const externalUrl = (tree.external_url ?? "").toLowerCase();
      return name.includes(kw) || id.includes(kw) || description.includes(kw) || externalUrl.includes(kw);
    });
  }, [trees, treeSearchKeyword]);

  const patchTreeFlags = async (
    record: FamilyTreeSummary,
    patch: Partial<Pick<FamilyTreeSummary, "has_source_document" | "has_hannom_text">>,
  ) => {
    setUpdatingFlagId(record.id);
    try {
      await updateFamilyTree(record.id, patch);
      setTrees((prev) =>
        prev.map((tree) => (tree.id === record.id ? { ...tree, ...patch } : tree)),
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Không thể cập nhật");
    } finally {
      setUpdatingFlagId(null);
    }
  };

  const openEditTreeFromList = (record: FamilyTreeSummary) => {
    setEditingTree(record);
    treeForm.setFieldsValue({
      name: record.name,
      description: record.description ?? "",
      external_url: record.external_url ?? "",
      has_source_document: !!record.has_source_document,
      has_hannom_text: !!record.has_hannom_text,
      is_public: !!record.is_public,
    });
    setTreeModalOpen(true);
  };

  const openCreateTreeModal = () => {
    setEditingTree(null);
    treeForm.setFieldsValue({
      name: "",
      description: "",
      external_url: "",
      has_source_document: false,
      has_hannom_text: false,
      is_public: false,
    });
    setTreeModalOpen(true);
  };

  const submitTreeForm = async (values: TreeFormValues) => {
    setSavingTree(true);
    try {
      const payload = {
        name: values.name,
        description: values.description || undefined,
        external_url: values.external_url?.trim() || null,
        has_source_document: !!values.has_source_document,
        has_hannom_text: !!values.has_hannom_text,
        is_public: !!values.is_public,
      };

      if (editingTree) {
        await updateFamilyTree(editingTree.id, payload);
        setTreeModalOpen(false);
        setEditingTree(null);
        await loadTrees();
      } else {
        const created = await createFamilyTree({
          name: values.name,
          description: values.description || undefined,
          external_url: payload.external_url,
          has_source_document: payload.has_source_document,
          has_hannom_text: payload.has_hannom_text,
          is_public: payload.is_public,
        });
        setTreeModalOpen(false);
        setEditingTree(null);
        await loadTrees();
        navigate(`/admin/gia-pha/${created.id}`);
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Cannot save tree");
    } finally {
      setSavingTree(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Typography.Title level={4} className="!mb-1">
            {t("pages.adminGiaPha.title", { defaultValue: "Quản lý gia phả" })}
          </Typography.Title>
          <Typography.Paragraph type="secondary" className="!mb-0">
            {t("familyTree.managerSubtitle", {
              defaultValue: "Quản lý danh sách cây gia phả. Bấm Chi tiết để xem và chỉnh sửa.",
            })}
          </Typography.Paragraph>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={() => loadTrees()} loading={loadingTrees}>
            {t("familyTree.reload", { defaultValue: "Tải lại" })}
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateTreeModal}>
            {t("familyTree.createTree", { defaultValue: "Tạo cây mới" })}
          </Button>
        </Space>
      </div>

      {pageError && (
        <Alert
          type="warning"
          showIcon
          className="mb-6"
          message={t("familyTree.errorTitle", { defaultValue: "Không tải được dữ liệu" })}
          description={pageError}
          closable
          onClose={() => setPageError(null)}
        />
      )}

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={8} md={6}>
          <Card>
            <Statistic
              title={t("familyTree.totalTrees", { defaultValue: "Tổng số cây gia phả" })}
              value={trees.length}
            />
          </Card>
        </Col>
      </Row>

      <Card title={t("familyTree.treeListTitle", { defaultValue: "Danh sách gia phả" })}>
        <Input.Search
          allowClear
          value={treeSearchKeyword}
          onChange={(event) => setTreeSearchKeyword(event.target.value)}
          placeholder={t("familyTree.searchTrees", { defaultValue: "Tìm cây theo tên, mã hoặc mô tả" })}
          className="mb-4 max-w-md"
        />

        <Table
          rowKey="id"
          loading={loadingTrees}
          dataSource={filteredTrees}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ["10", "20", "50"],
            showTotal: (total, range) => `${range[0]}-${range[1]} của ${total}`,
          }}
          scroll={{ x: 1400 }}
          locale={{
            emptyText: (
              <Empty
                description={t("familyTree.noTrees", { defaultValue: "Chưa có cây nào" })}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button type="primary" onClick={openCreateTreeModal}>
                  {t("familyTree.createTree", { defaultValue: "Tạo cây mới" })}
                </Button>
              </Empty>
            ),
          }}
          columns={[
            {
              title: t("familyTree.treeName", { defaultValue: "Gia phả" }).toUpperCase(),
              dataIndex: "name",
              fixed: "left",
              width: 240,
              render: (_name: string, record: FamilyTreeSummary) => (
                <div className="flex items-center gap-3 min-w-[200px]">
                  <Avatar
                    size={40}
                    className="shrink-0 !bg-primary/15 !text-primary"
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
              title: t("familyTree.treeDescription", { defaultValue: "Mô tả" }).toUpperCase(),
              dataIndex: "description",
              width: 300,
              render: (description: string | null | undefined) => {
                const text = description?.trim();
                if (!text) {
                  return (
                    <Typography.Text type="secondary">
                      {t("familyTree.noDescription", { defaultValue: "Không có mô tả" })}
                    </Typography.Text>
                  );
                }
                return (
                  <Typography.Paragraph
                    className="!mb-0"
                    ellipsis={{ rows: 2, expandable: true, symbol: "Xem thêm" }}
                  >
                    {text}
                  </Typography.Paragraph>
                );
              },
            },
            {
              title: t("familyTree.externalLink", { defaultValue: "Đường link" }).toUpperCase(),
              key: "external_url",
              width: 220,
              render: (_: unknown, record: FamilyTreeSummary) => {
                const url = getFamilyTreeExternalUrl(record);
                return (
                  <Typography.Link href={url} target="_blank" rel="noopener noreferrer" className="text-xs">
                    <LinkOutlined className="mr-1" />
                    {url.replace(/^https?:\/\//, "")}
                  </Typography.Link>
                );
              },
            },
            {
              title: t("familyTree.sourceDocument", { defaultValue: "Tài liệu gốc" }).toUpperCase(),
              key: "has_source_document",
              width: 120,
              align: "center",
              render: (_: unknown, record: FamilyTreeSummary) => (
                <Checkbox
                  checked={!!record.has_source_document}
                  disabled={updatingFlagId === record.id}
                  onChange={(event) =>
                    void patchTreeFlags(record, { has_source_document: event.target.checked })
                  }
                />
              ),
            },
            {
              title: t("familyTree.hannomText", { defaultValue: "Văn bản Hán Nôm" }).toUpperCase(),
              key: "has_hannom_text",
              width: 140,
              align: "center",
              render: (_: unknown, record: FamilyTreeSummary) => (
                <Checkbox
                  checked={!!record.has_hannom_text}
                  disabled={updatingFlagId === record.id}
                  onChange={(event) =>
                    void patchTreeFlags(record, { has_hannom_text: event.target.checked })
                  }
                />
              ),
            },
            {
              title: t("familyTree.totalMembers", { defaultValue: "Thành viên" }).toUpperCase(),
              dataIndex: "node_count",
              width: 120,
              render: (count: number) => (
                <Tag color={count > 0 ? "blue" : "default"}>
                  {count} {t("familyTree.membersShort", { defaultValue: "người" })}
                </Tag>
              ),
            },
            {
              title: t("familyTree.updatedAt", { defaultValue: "Cập nhật" }).toUpperCase(),
              dataIndex: "updated_at",
              width: 120,
              render: (value: string) => formatTreeDate(value),
            },
            {
              title: t("auth.actions", { defaultValue: "Thao tác" }),
              key: "actions",
              width: 240,
              align: "right",
              fixed: "right",
              render: (_: unknown, record: FamilyTreeSummary) => (
                <Space size={4} wrap className="justify-end">
                  <Button
                    type="link"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => navigate(`/admin/gia-pha/${record.id}`)}
                  >
                    {t("familyTree.detail", { defaultValue: "Chi tiết" })}
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => openEditTreeFromList(record)}
                  >
                    {t("familyTree.editTree", { defaultValue: "Sửa" })}
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    icon={<DownloadOutlined />}
                    onClick={() => navigate(`/admin/gia-pha/${record.id}?tab=documents`)}
                  >
                    {t("familyTree.downloadDocs", { defaultValue: "Tải tài liệu" })}
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={treeModalOpen}
        onCancel={() => {
          setTreeModalOpen(false);
          setEditingTree(null);
        }}
        title={
          editingTree
            ? t("familyTree.editTreeTitle", { defaultValue: "Sửa cây gia phả" })
            : t("familyTree.createTreeTitle", { defaultValue: "Tạo cây gia phả" })
        }
        footer={null}
        destroyOnClose
        width={640}
      >
        <Form form={treeForm} layout="vertical" onFinish={submitTreeForm}>
          <Form.Item
            label={t("familyTree.treeName", { defaultValue: "Tên cây" })}
            name="name"
            rules={[
              {
                required: true,
                message: t("familyTree.validationName", { defaultValue: "Vui lòng nhập tên cây" }),
              },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item label={t("familyTree.treeDescription", { defaultValue: "Mô tả" })} name="description">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item
            label={t("familyTree.externalLink", { defaultValue: "Đường link" })}
            name="external_url"
            extra="Ví dụ: https://vietnamgiapha.com/vpg-101"
          >
            <Input placeholder="https://vietnamgiapha.com/vpg-101" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={t("familyTree.sourceDocument", { defaultValue: "Tài liệu gốc" })}
                name="has_source_document"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label={t("familyTree.hannomText", { defaultValue: "Văn bản Hán Nôm" })}
                name="has_hannom_text"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label={t("familyTree.isPublic", { defaultValue: "Công khai (Guest xem được)" })}
            name="is_public"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <div className="flex justify-end gap-3">
            <Button onClick={() => setTreeModalOpen(false)}>
              {t("familyTree.cancel", { defaultValue: "Hủy" })}
            </Button>
            <Button type="primary" htmlType="submit" loading={savingTree}>
              {editingTree
                ? t("familyTree.save", { defaultValue: "Lưu thay đổi" })
                : t("familyTree.create", { defaultValue: "Tạo mới" })}
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default FamilyTreeManagerPage;
