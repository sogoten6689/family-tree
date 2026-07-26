import { ArrowRightOutlined } from "@ant-design/icons";
import { Alert, Button } from "antd";
import { Link } from "react-router-dom";

type Props = {
  message: string;
  nextLabel: string;
  nextHref: string;
  onClose?: () => void;
};

export function FlowNextBanner({ message, nextLabel, nextHref, onClose }: Props) {
  return (
    <Alert
      type="success"
      showIcon
      className="mb-4 flow-next-banner"
      message={message}
      action={
        <Link to={nextHref}>
          <Button type="primary" size="small" icon={<ArrowRightOutlined />}>
            {nextLabel}
          </Button>
        </Link>
      }
      closable={!!onClose}
      onClose={onClose}
    />
  );
}
