# UCI transfusion.data validation

Measured from the local file. Synthetic simulator assumptions are listed separately and are not findings about this table.

## Source

- Dataset: Blood Transfusion Service Center
- Origin: UCI Machine Learning Repository
- Citation: Yeh, I-Cheng (2008). Blood Transfusion Service Center. UCI Machine Learning Repository. CC BY 4.0.
- Geography: Hsin-Chu City, Taiwan. Not an Indian facility extract.
- Target: Whether the donor gave blood in March 2007 (1 = yes, 0 = no).
- SHA-256: `96c8e1091b9c037bcaf25a19b24b49d07771cd88689ffd273e056e9e8845ffe7`
- Header: `Recency (months),Frequency (times),Monetary (c.c. blood),Time (months),"whether he/she donated blood in March 2007"`

## Parsing and shape

- Rows: **748** (expected 748). Match: True.
- Columns: **5**. Names used after rename: Recency, Frequency, Monetary, Time, Donated.
- Physical lines including header: 749.
- File ends with a newline: False.

## Missing values and target

- Non-numeric or missing cells: 0.
- Target values observed: [0.0, 1.0].
- Binary 0/1 encoding: True.
- Donated in March 2007: 178 (0.2380).
- Did not donate: 570 (0.7620).
- Names file claims a 24% positive rate. Actual rate is 0.2380.

## Duplicates

- Extra copies: 215.
- Rows sitting in a duplicate group: 275.
- Unique rows if extras were ignored: 533.
- Duplicates were counted and kept. Nothing was deleted from transfusion.data.

## Descriptive statistics

| Variable | Min | Max | Mean | Sample std | Missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| Recency | 0.000 | 74.000 | 9.507 | 8.095 | 0 |
| Frequency | 1.000 | 50.000 | 5.515 | 5.839 | 0 |
| Monetary | 250.000 | 12500.000 | 1378.676 | 1459.827 | 0 |
| Time | 2.000 | 98.000 | 34.282 | 24.377 | 0 |
| Donated | 0.000 | 1.000 | 0.238 | 0.426 | 0 |

## Comparison with transfusion.names Table 1

The names file prints mins, maxes, means, and standard deviations that do not all match this CSV. Both are kept. The CSV is the file the simulator's calibration check uses.

| Variable | Names min | File min | Names max | File max | Names mean | File mean | Names std | File std |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Recency | 0.030 | 0.000 | 74.400 | 74.000 | 9.740 | 9.507 | 8.070 | 8.095 |
| Frequency | 1 | 1.000 | 50 | 50.000 | 5.510 | 5.515 | 5.840 | 5.839 |
| Monetary | 250 | 250.000 | 12500 | 12500.000 | 1378.680 | 1378.676 | 1459.830 | 1459.827 |
| Time | 2.270 | 2.000 | 98.300 | 98.000 | 34.420 | 34.282 | 24.320 | 24.377 |
| Donated | 0 | 0.000 | 1 | 1.000 | 0.240 | 0.238 | — | 0.426 |

## Consistency

- Rows where Monetary ≠ Frequency × 250: 0.
- Rows where Time < Recency: 0.

## Loyalty-tier calibration

The report's 14.4% and 36.6% anchors match frequency bins that keep tied Frequency values together. Those natural bins donate at 0.14444444444444443 and 0.36627906976744184 (gaps 0.00044444444444444176 and 0.00027906976744185297). Forcing four groups of equal size splits donors who share a frequency, and the highest group then sits slightly lower. Middle tiers 21.8% and 29.2% remain the report's interpolations. The simulator uses the published tier rates either way.

Donors were ranked by Frequency with method='first' so tied frequencies still form four groups of equal size. The rate is the share with Donated = 1.

| Quartile | n | Frequency min | Frequency max | Donated rate |
| --- | ---: | ---: | ---: | ---: |
| Q1_lowest_frequency | 187 | 1.0 | 2.0 | 0.1444 |
| Q2 | 187 | 2.0 | 4.0 | 0.1658 |
| Q3 | 187 | 4.0 | 7.0 | 0.2834 |
| Q4_highest_frequency | 187 | 7.0 | 50.0 | 0.3583 |

- Equal-count lowest gap vs 14.4%: 0.0004. Highest gap vs 36.6%: -0.0077.
- Natural-bin lowest gap vs 14.4%: 0.0004. Highest gap vs 36.6%: 0.0003.
- The report states that 21.8% and 29.2% are linear interpolations between the endpoint rates, not empirical middle-quartile rates. They are not tested as observed frequencies.

### Natural frequency bins

Bins from qcut on Frequency with duplicates='drop', so donors who share a frequency stay together.

- (0.999, 2.0]: n=270, donated rate=0.1444
- (2.0, 4.0]: n=149, donated rate=0.1812
- (4.0, 7.0]: n=157, donated rate=0.3121
- (7.0, 50.0]: n=172, donated rate=0.3663

## Not in this file

- ABO and Rh blood types
- Drive location or time slot
- Hospital stock or shortage
- Indian weekly turnout
- e-RaktKosh or NBTC facility records

## Limitations

- This file is the UCI Blood Transfusion Service Center donor table from Hsin-Chu City, Taiwan (Yeh, 2008). It does not contain blood types, drive locations, hospital inventory, or Indian weekly turnout.
- The e-RaktKosh / NBTC dataset cited in the project report is not in the workspace.
- transfusion.names prints a descriptive table (Recency mean 9.74, and a 24% / 76% class split) that does not match this file exactly. The audit keeps both and does not overwrite the data.
- Duplicate rows are reported and retained. They were not dropped.
- Simulator pool sizes, seasonality, ABO mix, and demand shares are synthetic assumptions. They are not estimated from these 748 rows, apart from the report's use of frequency-quartile return rates as loyalty anchors.
