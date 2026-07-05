import { Alert, Button, Card, Select, Spin, Table, Typography } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { deleteUser, fetchUsers, updateUserRole } from "@/lib/authApi";
import { ApiError } from "@/lib/apiClient";
import type { User, UserRole } from "@/types/auth";

const AdminUsersPage = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingUserId, setPendingUserId] = useState<number | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchUsers();
      setUsers(response.items);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t("auth.usersLoadFailed", { defaultValue: "Không thể tải danh sách user." }),
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const handleRoleChange = async (userId: number, role: UserRole) => {
    setPendingUserId(userId);
    setError(null);
    try {
      const updated = await updateUserRole(userId, role);
      setUsers((current) => current.map((user) => (user.id === updated.id ? updated : user)));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t("auth.roleUpdateFailed", { defaultValue: "Không thể cập nhật role." }),
      );
    } finally {
      setPendingUserId(null);
    }
  };

  const handleDelete = async (userId: number) => {
    setPendingUserId(userId);
    setError(null);
    try {
      await deleteUser(userId);
      setUsers((current) => current.filter((user) => user.id !== userId));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t("auth.userDeleteFailed", { defaultValue: "Không thể xóa user." }),
      );
    } finally {
      setPendingUserId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <Card>
        <Typography.Paragraph type="secondary">
          {t("auth.adminUsersDesc", {
            defaultValue: "Chỉ admin mới có thể xem, cập nhật role và xóa user.",
          })}
        </Typography.Paragraph>

        {error && <Alert type="error" message={error} showIcon className="mb-4" />}

        {loading ? (
          <div className="flex justify-center py-10">
            <Spin size="large" />
          </div>
        ) : (
          <Table
            rowKey="id"
            dataSource={users}
            pagination={false}
            scroll={{ x: 900 }}
            columns={[
              { title: "ID", dataIndex: "id", width: 70 },
              { title: t("auth.fullName", { defaultValue: "Họ và tên" }), dataIndex: "full_name" },
              { title: t("auth.email", { defaultValue: "Email" }), dataIndex: "email" },
              {
                title: "Role",
                dataIndex: "role",
                render: (role: UserRole, record: User) => (
                  <Select
                    value={role}
                    style={{ width: 120 }}
                    disabled={pendingUserId === record.id}
                    options={[
                      { value: "user", label: "user" },
                      { value: "admin", label: "admin" },
                    ]}
                    onChange={(value) => void handleRoleChange(record.id, value as UserRole)}
                  />
                ),
              },
              {
                title: t("auth.createdAt", { defaultValue: "Ngày tạo" }),
                dataIndex: "created_at",
                render: (value: string) => new Date(value).toLocaleString("vi-VN"),
              },
              {
                title: t("auth.actions", { defaultValue: "Thao tác" }),
                render: (_: unknown, record: User) => (
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    disabled={pendingUserId === record.id}
                    onClick={() => void handleDelete(record.id)}
                  >
                    {t("auth.delete", { defaultValue: "Xóa" })}
                  </Button>
                ),
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
};

export default AdminUsersPage;
