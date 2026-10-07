import re, subprocess, sys, json
out = {}
for y in range(2016, 2025):
    t = subprocess.run(["pdftotext", f"{sys.argv[1]}/NVSR_births_final_{y}.pdf", "-"], capture_output=True, text=True).stdout
    t = re.sub(r"\s+", " ", t)
    sents = re.split(r"(?<=[a-z0-9)%])\. (?=[A-Z])", t)
    def pick(pat):
        for s in sents:
            if re.search(pat, s): return s.strip()[:260]
        return None
    out[y] = {
      "births": pick(r"births were registered"),
      "ptb_all": pick(r"[Pp]reterm birth rate (rose|declined|was|increased|decreased|was unchanged|was essentially)[^%]*%.*?(in|from|to) ?\d{4}|preterm birth rate (rose|declined) \d% (in \d{4} )?to"),
      "ptb_singleton": pick(r"preterm birth rate for singleton births only"),
      "lbw_all": pick(r"percentage of infants born low birthweight|[Ll]ow birthweight rate (rose|declined|also rose|was|decreased|declined)|LBW rate (rose|declined|was|decreased|increased) (\d% )?(in|from|to|for|unchanged)"),
      "lbw_singleton": pick(r"LBW rate among singleton births only"),
    }
json.dump(out, open(sys.argv[2], "w"), indent=1)
for y, d in out.items():
    print("==", y)
    for k, v in d.items(): print(f"  {k}: {v}")
