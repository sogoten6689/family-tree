import { Input, Table, Tag } from "antd";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";

type Props = {
  members: FamilyMember[];
  onSelectMember?: (memberId: number) => void;
};

export function FamilyTreeMembersTable({ members, onSelectMember }: Props) {
  const { t } = useTranslation();
  const [keyword, setKeyword] = useState("");

  const filteredMembers = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    if (!kw) return members;
    return members.filter(
      (member) =>
        member.name.toLowerCase().includes(kw) ||
        String(member.generation).includes(kw) ||
        (member.title?.toLowerCase().includes(kw) ?? false),
    );
  }, [members, keyword]);

  return (
    <div>
      <Input.Search
        allowClear
        placeholder={t("familyTree.searchMembers", { defaultValue: "Tìm thành viên theo tên, đời..." })}
        value={keyword}
        onChange={(event) => setKeyword(event.target.value)}
        className="mb-4 max-w-md"
      />
      <Table
        rowKey="id"
        size="small"
        dataSource={filteredMembers}
        pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ["10", "20", "50"] }}
        onRow={(record) =>
          onSelectMember
            ? {
                onClick: () => onSelectMember(Number(record.id)),
                className: "cursor-pointer",
              }
            : {}
        }
        columns={[
          {
            title: t("familyTree.fullName", { defaultValue: "Họ và tên" }),
            dataIndex: "name",
            render: (name: string, record: FamilyMember) => (
              <div>
                <div className="font-medium">{name}</div>
                {record.title && (
                  <Tag color="gold" className="!mt-1">
                    {record.title}
                  </Tag>
                )}
              </div>
            ),
          },
          {
            title: t("familyTree.generation", { defaultValue: "Đời thứ" }),
            dataIndex: "generation",
            width: 90,
            sorter: (a, b) => a.generation - b.generation,
          },
          {
            title: t("familyTree.birthYear", { defaultValue: "Năm sinh" }),
            dataIndex: "birthYear",
            width: 100,
            render: (year: number) => (year > 0 ? year : "—"),
          },
          {
            title: t("familyTree.gender", { defaultValue: "Giới tính" }),
            dataIndex: "gender",
            width: 90,
            render: (gender: FamilyMember["gender"]) =>
              gender === "male"
                ? t("familyTree.male", { defaultValue: "Nam" })
                : t("familyTree.female", { defaultValue: "Nữ" }),
          },
        ]}
      />
    </div>
  );
}
