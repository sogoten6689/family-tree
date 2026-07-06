import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Button,
  Card,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Row,
  Col,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  BranchesOutlined,
  CloudDownloadOutlined,
  EditOutlined,
  FileTextOutlined,
  LinkOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  createFamilyTree,
  crawlAndSyncVietnamGiaPha,
  listFamilyTrees,
  updateFamilyTree,
  type FamilyTreeDocument,
  type FamilyTreeSummary,
} from "@/lib/familyTreeApi";
import { formatTreeDate, getFamilyTreePublicUrl } from "@/lib/familyTreeUtils";

type TreeFormValues = {
  name: string;
  description?: string;
};

type CrawlFormValues = {
  startId: number;
  endId: number;
  delaySeconds?: number;
  syncDb: boolean;
};

const FamilyTreeManagerPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [trees, setTrees] = useState<FamilyTreeSummary[]>([]);
  const [loadingTrees, setLoadingTrees] = useState(false);
  const [savingTree, setSavingTree] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [treeModalOpen, setTreeModalOpen] = useState(false);
  const [editingTree, setEditingTree] = useState<FamilyTreeDocument | null>(null);
  const [crawlModalOpen, setCrawlModalOpen] = useState(false);
  const [crawlingData, setCrawlingData] = useState(false);
  const [treeSearchKeyword, setTreeSearchKeyword] = useState("");

  const [treeForm] = Form.useForm<TreeFormValues>();
  const [crawlForm] = Form.useForm<CrawlFormValues>();

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
      return name.includes(kw) || id.includes(kw) || description.includes(kw);
    });
  }, [trees, treeSearchKeyword]);

  const openEditTreeFromList = (record: FamilyTreeSummary) => {
    setEditingTree({
      id: record.id,
      name: record.name,
      description: record.description,
      created_at: record.created_at,
      updated_at: record.updated_at,
      nodes: [],
    });
    treeForm.setFieldsValue({ name: record.name, description: record.description ?? "" });
    setTreeModalOpen(true);
  };

  const openCreateTreeModal = () => {
    setEditingTree(null);
    treeForm.setFieldsValue({ name: "", description: "" });
    setTreeModalOpen(true);
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

  const submitTreeForm = async (values: TreeFormValues) => {
    setSavingTree(true);
    try {
      if (editingTree) {
        await updateFamilyTree(editingTree.id, values);
        setTreeModalOpen(false);
        setEditingTree(null);
        await loadTrees();
      } else {
        const created = await createFamilyTree({
          name: values.name,
          description: values.description || undefined,
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
      await loadTrees();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Không thể crawl/sync dữ liệu");
    } finally {
      setCrawlingData(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Typography.Paragraph type="secondary" className="!mb-0">
          {t("familyTree.managerSubtitle", {
            defaultValue: "Quản lý danh sách cây gia phả. Bấm Chi tiết để xem và chỉnh sửa.",
          })}
        </Typography.Paragraph>
        <div className="flex flex-wrap items-center gap-3">
          <Button icon={<CloudDownloadOutlined />} onClick={openCrawlModal} loading={crawlingData}>
            {t("familyTree.crawlSync", { defaultValue: "Crawl + Sync DB" })}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => loadTrees()} loading={loadingTrees}>
            {t("familyTree.reload", { defaultValue: "Tải lại" })}
          </Button>
          <Button icon={<PlusOutlined />} onClick={openCreateTreeModal} type="primary">
            {t("familyTree.createTree", { defaultValue: "Tạo cây mới" })}
          </Button>
        </div>
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

      <Card
        title={t("familyTree.treeListTitle", { defaultValue: "Danh sách gia phả" })}
        extra={<Tag>{filteredTrees.length}</Tag>}
      >
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
          pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ["10", "20", "50"] }}
          scroll={{ x: 1100 }}
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
              render: (_name: string, record: FamilyTreeSummary) => (
                <div className="flex items-center gap-3 min-w-[220px]">
                  <Avatar
                    size={40}
                    className="shrink-0 !bg-[#1677ff]/15 dark:!bg-[#1677ff]/25 !text-[#1677ff] dark:!text-[#69b1ff]"
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
              width: 280,
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
              title: t("familyTree.totalMembers", { defaultValue: "Thành viên" }).toUpperCase(),
              dataIndex: "node_count",
              width: 130,
              render: (count: number) => (
                <Tag color={count > 0 ? "blue" : "default"}>
                  {count} {t("familyTree.membersShort", { defaultValue: "người" })}
                </Tag>
              ),
            },
            {
              title: t("familyTree.linkColumn", { defaultValue: "Liên kết" }).toUpperCase(),
              key: "link",
              width: 100,
              align: "center",
              render: (_: unknown, record: FamilyTreeSummary) => (
                <Button
                  type="link"
                  icon={<LinkOutlined />}
                  href={getFamilyTreePublicUrl(record.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t("familyTree.openLink", { defaultValue: "Mở" })}
                </Button>
              ),
            },
            {
              title: t("familyTree.updatedAt", { defaultValue: "Cập nhật" }).toUpperCase(),
              dataIndex: "updated_at",
              width: 130,
              render: (value: string) => formatTreeDate(value),
            },
            {
              title: t("auth.actions", { defaultValue: "Thao tác" }),
              key: "actions",
              width: 220,
              align: "right",
              fixed: "right",
              render: (_: unknown, record: FamilyTreeSummary) => (
                <div className="flex flex-wrap justify-end gap-1">
                  <Button
                    type="link"
                    size="small"
                    className="!px-1"
                    onClick={() => navigate(`/admin/gia-pha/${record.id}`)}
                  >
                    {t("familyTree.detail", { defaultValue: "Chi tiết" })}
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    className="!px-1"
                    icon={<EditOutlined />}
                    onClick={() => openEditTreeFromList(record)}
                  >
                    {t("familyTree.editTree", { defaultValue: "Sửa" })}
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    className="!px-1"
                    icon={<FileTextOutlined />}
                    onClick={() => navigate(`/admin/gia-pha/${record.id}?tab=documents`)}
                  >
                    {t("familyTree.documentsTab", { defaultValue: "Tài liệu" })}
                  </Button>
                </div>
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

      <Modal
        open={crawlModalOpen}
        onCancel={() => setCrawlModalOpen(false)}
        title={t("familyTree.crawlSyncTitle", { defaultValue: "Crawl dữ liệu và đồng bộ database" })}
        footer={[
          <Button key="cancel" onClick={() => setCrawlModalOpen(false)}>
            {t("familyTree.cancel", { defaultValue: "Hủy" })}
          </Button>,
          <Button key="run" type="primary" loading={crawlingData} onClick={() => crawlForm.submit()}>
            {t("familyTree.run", { defaultValue: "Chạy" })}
          </Button>,
        ]}
        destroyOnClose
      >
        <Form form={crawlForm} layout="vertical" onFinish={submitCrawlForm}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label={t("familyTree.startId", { defaultValue: "ID bắt đầu" })}
                name="startId"
                rules={[{ required: true, message: "Nhập ID bắt đầu" }]}
              >
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label={t("familyTree.endId", { defaultValue: "ID kết thúc" })}
                name="endId"
                rules={[{ required: true, message: "Nhập ID kết thúc" }]}
              >
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label={t("familyTree.delaySeconds", { defaultValue: "Delay giữa request (giây)" })}
            name="delaySeconds"
          >
            <InputNumber min={0} max={5} step={0.1} className="w-full" />
          </Form.Item>
          <Form.Item label={t("familyTree.syncDb", { defaultValue: "Đồng bộ database" })} name="syncDb">
            <Radio.Group>
              <Radio value>{t("common.yes", { defaultValue: "Có" })}</Radio>
              <Radio value={false}>{t("common.no", { defaultValue: "Không" })}</Radio>
            </Radio.Group>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FamilyTreeManagerPage;
