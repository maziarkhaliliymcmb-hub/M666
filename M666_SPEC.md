# M666 Interaction Matrix 1.0.0

M666 addresses the 666 unordered gene-pairs-with-self-interaction in a 36-gene genome:
C(36,2) + 36 = 630 + 36 = 666 = T36.

The matrix is symmetric: (i,j) and (j,i) resolve to the same canonical slot. The 36 diagonal positions represent self-regulation. This is an address-space capacity, not a requirement to materialize 666 rows. The implementation is sparse and stores only explicitly defined relations.

Each relation carries type, signed weight, confidence, and status. Values must come from evidence, tests, or documented policy; the library does not invent them. M666 is separate from M1296: M666 models symmetric association, while M1296 models directed influence.
