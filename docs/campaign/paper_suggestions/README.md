# Testing the improvements suggested in arXiv:1806.07517

The HFOFO paper closes (sec. 7 "Comments", plus sec. 4) with suggested
improvements. Artifacts from testing each of them:

- `screen_runs.csv` — seed-1 screening matrix: quadrupole equalization field
  (Gq -0.026/-0.052/-0.078 T/m, incl. 45-degree roll) and z-tapered dipole
  strength (pitchTaperStart/End), each on both the nominal and taperB2
  backgrounds (10 designs, 400 events).
- `gq_confirm_runs.csv` — seeds 2-3 confirmation that the apparent
  transmission gain of Gq=-0.078 T/m on seed 1 does not reproduce.
- `phaseP_trials.csv` — Phase P: 24-trial TPE scan of high solenoid focusing
  (BLS 22.5-30, all other knobs co-tuned) testing the "higher betatron phase
  advance" suggestion. Includes clean BLS = 23/25/27/29 anchors on the
  taperB2 wedge shape.
- `phaseP_validation_runs.csv` — 3-seed validation of the best Phase P design
  (BLS 22.5): T=0.596+/-0.007, eps6D=101+/-17 — matches but does not beat
  taperB2.

Conclusions and the length-taper feasibility analysis: campaign report sec. 6c.
