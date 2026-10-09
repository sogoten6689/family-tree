import "@testing-library/jest-dom";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// jsdom so khớp TỪNG luật CSS đã chèn vào trang (nwsapi) mỗi lần getComputedStyle được gọi —
// mà getByRole/accessible-name của Testing Library gọi hàm này cho từng phần tử. Với CSS của
// antd (hàng nghìn luật) một lần gọi mất ~360 ms, một bài test render Select/Popconfirm/Table
// mất 20–600 giây và làm CI Frontend treo 20 phút. Test không cần CSS thật của antd, nên bỏ
// các thẻ <style> mà cssinjs chèn vào <head> (trình duyệt thật không bị ảnh hưởng).
const stripStyles = () => {
  document.head.querySelectorAll("style").forEach((node) => node.remove());
};
new MutationObserver(stripStyles).observe(document.head, { childList: true });
