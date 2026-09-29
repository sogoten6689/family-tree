import bertalign
import sys
from bertalign import Encoder

src_par_path = sys.argv[1]
tgt_par_path = sys.argv[2]
alignments_path = sys.argv[3]

src_par = ""
tgt_par = ""

with open(src_par_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
    for line in lines:
        src_par += line.strip() + "\n"

with open(tgt_par_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
    for line in lines:
        tgt_par += line.strip() + "\n"
    

aligner = bertalign.Bertalign(src=src_par, tgt=tgt_par)

aligner.align_sents()

alignments = []
for bead in (aligner.result):
    src_line = aligner._get_line(bead[0], aligner.src_sents)
    tgt_line = aligner._get_line(bead[1], aligner.tgt_sents)
    # calculate similarity
    alignments.append((src_line, tgt_line))

with open(alignments_path, "w", encoding="utf-8") as f:
    for i in range(len(alignments)):
        f.write(f"{alignments[i][0]}\t{alignments[i][1]}\n")