import { Card, Tag, Tooltip } from 'antd';
import { UserOutlined, ManOutlined, WomanOutlined } from '@ant-design/icons';
import type { FamilyMember } from '@/data/familyMockData';

interface Props {
  member: FamilyMember;
  onSelect: (member: FamilyMember) => void;
  isSelected: boolean;
}

const FamilyTreeNode = ({ member, onSelect, isSelected }: Props) => {
  const isMale = member.gender === 'male';
  const isDeceased = !!member.deathYear;

  return (
    <Tooltip title="Nhấn để xem chi tiết">
      <div
        className={`tree-node-card cursor-pointer p-4 min-w-[180px] max-w-[220px] ${isSelected ? 'ring-2 ring-gold shadow-lg' : ''}`}
        onClick={() => onSelect(member)}
        style={{
          borderColor: isMale ? 'hsl(36, 70%, 42%)' : 'hsl(0, 45%, 35%)',
          opacity: isDeceased ? 0.85 : 1,
        }}
      >
        <div className="flex items-center gap-2 mb-2">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
            style={{
              background: isMale ? 'hsl(36, 70%, 42%)' : 'hsl(0, 45%, 35%)',
              color: 'hsl(39, 50%, 96%)',
            }}
          >
            {isMale ? <ManOutlined /> : <WomanOutlined />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-semibold text-sm text-foreground truncate">{member.name}</div>
            <div className="text-xs text-muted-foreground">
              {member.birthYear}{member.deathYear ? ` - ${member.deathYear}` : ' - nay'}
            </div>
          </div>
        </div>
        {member.title && (
          <Tag
            color="gold"
            className="text-xs"
            style={{ fontFamily: 'var(--font-body)' }}
          >
            {member.title}
          </Tag>
        )}
        {member.spouseName && (
          <div className="text-xs text-muted-foreground mt-1">
            ♥ {member.spouseName}
          </div>
        )}
      </div>
    </Tooltip>
  );
};

export default FamilyTreeNode;
