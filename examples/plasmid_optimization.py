"""Example of plasmid optimization with DnaChisel.

In this example, we download a plasmid from the web in GENBANK format and
modify the sequence with respect to the following constraints and objectives:

- For each coding sequence (CDS) found in the Genbank file:
    - Make sure the corresponding protein sequence remains unchanged.
    - Do not modify the 30-base-pair region upstream of the CDS (promoter)
    - Codon-optimize for E. coli (use the most frequent codons preferentially)

- Enforce the constraints given by the DNA provider Gen9:
    - Make sure there is no restriction site for BsaI and AarI in the sequence
    - Make sure there is no 9-homopolymers of A,T,C or any 6-homopolymers of G.
    - Make sure the GC content remains between 40 and 65 percent globally and
      between 25 and 80 percent over sliding 100-base-pair windows

- Aim at a global GC content of 51 percent like in E. coli

At the beginning, many of the constraints fail (there are BsaI sites, A- and T-
homopolymers, and the GC-content is out-of-bounds in many locations).
After a run of the constraint solver (~ 1 second) all constraints are solved.
And after a run of the optimization algorithm (~20 seconds) the objectives are
much improved.

The final sequence (with the original annotations) is exported to Genbank.
"""

import urllib
from dnachisel import *
from Bio import SeqIO, Seq

# DOWNLOAD THE PLASMID FROM THE WEB (it is a 7kb plasmid with 3 genes)

url = "http://www.stevekellylab.com/constructs/pDex/pDex577-G.gb"
urllib.urlretrieve(url, "pDex577-G.gb")


# PARSE THE PLASMID FILE WITH BIOPYTHON, GET ITS SEQUENCE AND GENES LOCATIONS

annotated_sequence = SeqIO.read(open("pDex577-G.gb"), "genbank")
sequence = str(annotated_sequence.seq)
CDS_list = [
    (int(f.location.start), int(f.location.end), int(f.location.strand))
    for f in annotated_sequence.features
    if f.type == "CDS"
]


# DEFINE ALL THE CONSTRAINTS

GEN9_constraints = [
    AvoidPattern(enzyme_pattern("BsaI")),
    AvoidPattern(enzyme_pattern("AarI")),
    AvoidPattern(homopolymer_pattern("A", 9)),
    AvoidPattern(homopolymer_pattern("T", 9)),
    AvoidPattern(homopolymer_pattern("G", 6)),
    AvoidPattern(homopolymer_pattern("C", 9)),
    EnforceGCContent(0.4, 0.65),
    EnforceGCContent(0.25, 0.80, window=50)
]

CDS_constraints = []
for (start, end, strand) in CDS_list:
    if strand == 1:
        promoter_region = Location(start - 30, start - 1)
    else:
        promoter_region = Location(end + 1, end + 30)
    keep_promoter_region = AvoidChanges(promoter_region)
    keep_translation = EnforceTranslation(Location(start, end, strand))
    CDS_constraints += [keep_promoter_region, keep_translation]


# DEFINE ALL THE OBJECTIVES

objectives = [EnforceGCContent(0.51, boost=10000)] + [
    CodonOptimize("e_coli", location=Location(start, end, strand=strand))
    for (start, end, strand) in CDS_list
]


# DEFINE AND SOLVE THE PROBLEM

problem = DnaOptimizationProblem(
    sequence=sequence,
    constraints=GEN9_constraints + CDS_constraints,
    objectives=objectives
)

print ("\n\n=== Initial Status ===")
print (problem.constraints_text_summary(failed_only=True))
print (problem.objectives_text_summary())
import time

print ("Now solving constraints...")
problem.solve_all_constraints_one_by_one()
print (problem.constraints_text_summary(failed_only=True))

print ("Now optimizing objectives...")

problem.maximize_all_objectives_one_by_one(max_random_iters=2000)

print ("\n\n=== Status after optimization ===\n\n")
print (problem.objectives_text_summary())
print ("Let us check again on the constraints:")
print (problem.constraints_text_summary(failed_only=True))

# Write the final sequence back to GENBANK (annotations are conserved)

annotated_sequence.seq = Seq.Seq(problem.sequence,
                                 annotated_sequence.seq.alphabet)
SeqIO.write(annotated_sequence, open("result.gb", "w+"), "genbank")
