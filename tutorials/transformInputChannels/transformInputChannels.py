
from pyppl import PyPPL, Proc, Channel


pSort        = Proc(desc = 'Sort files.')
pSort.input  = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output = "outfile:file:{{i.infile | fn}}.sorted"
pSort.forks  = 5
pSort.script = """
  sort -k1r {{i.infile}} > {{o.outfile}}
"""

pAddPrefix         = Proc(desc = 'Add line number to each line.')
pAddPrefix.depends = pSort
pAddPrefix.input   = "infile:file"  # automatically inferred from pSort.output
pAddPrefix.output  = "outfile:file:{{i.infile | fn}}.ln"
pAddPrefix.forks   = 5
pAddPrefix.script  = """
paste -d. <(seq 1 $(wc -l {{i.infile}} | cut -f1 -d' ')) {{i.infile}} > {{o.outfile}}
"""

pMergeFiles = Proc(desc = 'Merge files, each as a column.')
pMergeFiles.depends = pAddPrefix
# ["test1.ln", "test2.ln", ..., "test5.ln"]
pMergeFiles.input = {"infiles:files": lambda ch: [ch.flatten()]}
pMergeFiles.output = "outfile:file:mergedfile.txt"
pMergeFiles.exdir = "./export"
pMergeFiles.script = """
paste {{i.infiles | asquote}} > {{o.outfile}}
"""

PyPPL().start(pSort).run()
