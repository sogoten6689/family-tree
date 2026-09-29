import sys
import bertalign
from bertalign import Encoder
import os
from fastapi import FastAPI, Request
import uvicorn

sys.path.append('./bertalign')
os.chdir('./')

def replace_endline(text: str, lang: str) -> str:
  if lang != 'zh' and lang != 'vi':
    raise Exception("language not supported")
  res = ""
  if lang == 'zh':
    res = text.replace('\n', '。')
    res = res.replace('。。', '。')
    res = res.replace('。”。', '。”')
  elif lang == 'vi':
    res = text.replace('\n', '. ')
    res = res.replace('..', '.')
  return res

def align_par(src_par: str, tgt_par: str) -> str:
  src_par = replace_endline(src_par, 'zh')
  tgt_par = replace_endline(tgt_par, 'vi')

  aligner = bertalign.Bertalign(src=src_par, tgt=tgt_par)

  aligner.align_sents()

  alignments = []
  for bead in (aligner.result):
    src_line = aligner._get_line(bead[0], aligner.src_sents)
    tgt_line = aligner._get_line(bead[1], aligner.tgt_sents)
    # calculate similarity
    alignments.append((src_line, tgt_line))

  res: str = ""
  for i in range(len(alignments)):
    res += alignments[i][0] + "\t" + alignments[i][1] + "\n"

  return res

# src_par = """
# 话说天下大势，分久必合，合久必分。周末七国分争，并入于秦。及秦灭之后，楚、汉分争，又并入于汉。汉朝自高祖斩白蛇而起义，一统天下，后来光武中兴，传至献帝，遂分为三国。推其致乱之由，殆始于桓、灵二帝。桓帝禁锢善类，崇信宦官。及桓帝崩，灵帝即位，大将军窦武、太傅陈蕃共相辅佐。时有宦官曹节等弄权，窦武、陈蕃谋诛之，机事不密，反为所害，中涓自此愈横。
# """

# tgt_par = """
# Thế lớn trong thiên hạ, cứ tan lâu rồi lại hợp, hợp lâu rồi lại tan: Như cuối đời nhà Chu, bảy nước tranh giành xâu xé nhau rồi sau lại hợp về nhà Tần. Đến khi nhà Tần mất, thì Hán Sở tranh hùng rồi sau thiên hạ lại hợp về tay nhà Hán. Nhà Hán, từ lúc vua Cao tổ (Bái Công) chém rắn trắng khởi nghĩa, thống nhất được thiên hạ, sau vua Quang Vũ lên ngôi, rồi truyền mãi đến vua Hiến Đế; lúc bấy giờ lại chia ra thành ba nước. Nguyên nhân gây ra biến loạn ấy là do hai vua Hoàn đế, Linh đế. Vua Hoàn đế tin dùng lũ hoạn quan, cấm cố những người hiền sĩ. Đến lúc vua Hoàn đế băng hà, vua Linh đế lên ngôi nối nghiệp; được quan đại tướng quân Đậu Vũ, quan thái phó Trần Phồn giúp đỡ. Khi ấy, trong triều có bọn hoạn quan là lũ Tào Tiết lộng quyền. Đậu Vũ, Trần Phồn lập mưu định trừ bọn ấy đi, nhưng vì cơ mưu tiết lộ nên lại bị chúng nó giết mất. Từ đấy, bọn hoạn quan ngày càng bạo ngược.
# """

# alignments = align_par(src_par, tgt_par)
# print(alignments)

app = FastAPI(debug=True)

@app.get("/")
async def hello():
  return {"message": "Hello, World!"}

@app.post("/api/alignment")
async def sentence_alignment(request: Request):
  try:
    request_data = await request.json()
    print (request_data)
    alignments = align_par(request_data['src_text'], request_data['tgt_text'])
    print (alignments)
    return {"data": alignments}
  except Exception as e:
    print(f"Error: {e}")
    return {"data": ""}

if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
