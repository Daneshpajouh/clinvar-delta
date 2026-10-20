# Data sources

All raw data sit in a data directory outside the repository (`DATA_DIR` below).
`scripts/fetch_data.sh DATA_DIR STAGE...` downloaded them on 2026-10-19 and wrote one row per file to
`DATA_DIR/provenance.tsv`. The table below is that file. The files total 1.51 GB.

Checks run after download: the two ClinVar files match their NCBI `.md5` files; the GIAB VCF MD5
(`dc750b3807d4af1f7ffec852e9c2f771`) matches the value stored on the S3 object; all 23 UCSC
chromosome files match `md5sum.txt` from the same folder.

## Access route and robots.txt

- GIAB: fetched from the AWS Open Data mirror (`giab.s3.amazonaws.com`), which has no robots.txt.
  The NCBI host `ftp-trace.ncbi.nlm.nih.gov` serves a robots.txt that disallows all agents over HTTPS.
- ClinVar: `ftp.ncbi.nlm.nih.gov` also disallows all agents in its HTTPS robots.txt. The files were
  fetched over the anonymous FTP service of the same host, which NCBI documents for bulk download
  and which robots.txt does not cover. One request per named file, no directory crawling beyond
  two listings to find the release names.
- UCSC `hgdownload.soe.ucsc.edu`: robots.txt blocks a list of named crawlers only.
- gnomAD: `storage.googleapis.com` public bucket; only the panel regions were read, using the remote
  tabix index (htslib range requests), so about 35 MB came down instead of the full genome files.
- Ensembl REST (`rest.ensembl.org`): no robots.txt; one POST to `/lookup/symbol/homo_sapiens` with
  81 symbols; `/info/data` reported Ensembl release 116.
- NCBI ACMG page (`www.ncbi.nlm.nih.gov/clinvar/docs/acmg/`): allowed by that host's robots.txt.

## Files

| Stage | URL | Local path | Bytes | SHA-256 | Fetched (UTC) |
|---|---|---|---|---|---|
| giab | https://giab.s3.amazonaws.com/release/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz | giab/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz | 156,252,944 | `adb4d4a50048aa13353a06b84fcfcbca09a5d17525efaa4cea44f8822e81175c` | 2026-10-19T18:12:08Z |
| giab | https://giab.s3.amazonaws.com/release/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi | giab/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi | 1,657,747 | `23162712553413b10f88916c28bd1238deb703a7237be2910440773beea71894` | 2026-10-19T18:12:09Z |
| clinvar | ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar_20261011.vcf.gz.md5 | clinvar/clinvar_20261011.vcf.gz.md5 | 132 | `0965e9d88c72230cf9b438148a8fe03488f28898a5ca451cc891ca32ecfab914` | 2026-10-19T18:12:11Z |
| clinvar | ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar_20261011.vcf.gz | clinvar/clinvar_20261011.vcf.gz | 200,437,060 | `05d9481dd7217cc4df15803362d4a4c9eae5875b27b1750867d6bfd2643b3d10` | 2026-10-19T18:12:21Z |
| clinvar | ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar_20261011.vcf.gz.tbi | clinvar/clinvar_20261011.vcf.gz.tbi | 612,038 | `1a8e2b66684b4b3f4ca441274777c254f0405e10e304d0e5c08aabeaad8f0dd2` | 2026-10-19T18:12:23Z |
| clinvar | ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/archive_2.0/2025/clinvar_20251013.vcf.gz.md5 | clinvar/clinvar_20251013.vcf.gz.md5 | 132 | `5098705e005cb5135f1e8bff7a9f257adc0f05c5d5fc4ecae9de6b10c7916704` | 2026-10-19T18:12:25Z |
| clinvar | ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/archive_2.0/2025/clinvar_20251013.vcf.gz | clinvar/clinvar_20251013.vcf.gz | 174,939,681 | `8027cc605e98371984f899814b6332c3e500b0ea888b953bb1b432c242f3ab3c` | 2026-10-19T18:12:35Z |
| clinvar | ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/archive_2.0/2025/clinvar_20251013.vcf.gz.tbi | clinvar/clinvar_20251013.vcf.gz.tbi | 571,701 | `8b7b4d96a96f39166514f1fb8690b13502d4739ffd26cbfda62e2c5720bb1225` | 2026-10-19T18:12:38Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/md5sum.txt | reference/ucsc/md5sum.txt | 26,851 | `26b936ef7d4dc6a3d23f15743fb9657e671289a8643baa2522a3d235391698ef` | 2026-10-19T18:12:38Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr1.fa.gz | reference/ucsc/chr1.fa.gz | 74,778,116 | `baf03990d81ed87d66a976779c2eb4d8a0e5243829ca913556d3819fe0fba696` | 2026-10-19T18:12:42Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr2.fa.gz | reference/ucsc/chr2.fa.gz | 78,561,132 | `748007e198312d16d6277dcdd48d4f050109273cacf1a7a09860f965f2060555` | 2026-10-19T18:12:45Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr3.fa.gz | reference/ucsc/chr3.fa.gz | 64,527,121 | `8085449fc0da498712ce08476ebe06dfc885a5421cb742eebacf35bcf1c9fce1` | 2026-10-19T18:12:48Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr4.fa.gz | reference/ucsc/chr4.fa.gz | 61,949,239 | `0f50973dd3c9511c484f68bf83f0a75026d10f6544ee4c23fed6c06e7fd2a5dd` | 2026-10-19T18:12:51Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr5.fa.gz | reference/ucsc/chr5.fa.gz | 58,835,176 | `a29cb40486d4fcfcae187594809846df4cd4f10169045965bec987395ad714a2` | 2026-10-19T18:12:54Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr6.fa.gz | reference/ucsc/chr6.fa.gz | 55,575,966 | `88b83042e9e06f50a35394c46aa9af806b757a3c1fa7765318ea5f7fa7658174` | 2026-10-19T18:12:57Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr7.fa.gz | reference/ucsc/chr7.fa.gz | 51,118,425 | `455aa4c3faee9fbb952799db56a918dbc6850317c3c9c345e3b74e69d316a21a` | 2026-10-19T18:12:59Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr8.fa.gz | reference/ucsc/chr8.fa.gz | 47,076,040 | `68d2be09d82c39c254ddde43523d14741da18d7b9dc2ac646bd3d5569ff87671` | 2026-10-19T18:13:02Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr9.fa.gz | reference/ucsc/chr9.fa.gz | 39,441,862 | `dc07c4ea08008635d5827f806fbec3c2723c5c9dd4f47fe947f4e91f1c1a535f` | 2026-10-19T18:13:04Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr10.fa.gz | reference/ucsc/chr10.fa.gz | 43,157,332 | `4425ab3327d51791e1c2361ffb283bb732ca77cfa1d76b9118d0f8eae1a568c8` | 2026-10-19T18:13:06Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr11.fa.gz | reference/ucsc/chr11.fa.gz | 43,168,911 | `2d8357fd5caa888cd4b6c16ebd6c249250fbc03d940447666de21d91f371726c` | 2026-10-19T18:13:08Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr12.fa.gz | reference/ucsc/chr12.fa.gz | 42,940,449 | `13a3a52fa31c74488c818adf3d7928620d7ec9c0f01c1147816723cd1fb38f95` | 2026-10-19T18:13:10Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr13.fa.gz | reference/ucsc/chr13.fa.gz | 31,870,393 | `73da1d4cc471e4c2104c31a9a2bd34ed2918a14bf6af058a68eda3a1fefb9636` | 2026-10-19T18:13:12Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr14.fa.gz | reference/ucsc/chr14.fa.gz | 29,295,890 | `7c41d84d3f9e6f718d2c5201b781716293c1cbaefbf09dcfe9b33d957fe3f23b` | 2026-10-19T18:13:13Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr15.fa.gz | reference/ucsc/chr15.fa.gz | 27,201,183 | `0e0d988d6cbdf9fe424e1847a2278aa3ff9636b08663a6dd32c046f001dcf427` | 2026-10-19T18:13:15Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr16.fa.gz | reference/ucsc/chr16.fa.gz | 26,106,261 | `588201116a650cffa36b15a9a37cd149db63b0790485fd6653cbba6be89371ed` | 2026-10-19T18:13:17Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr17.fa.gz | reference/ucsc/chr17.fa.gz | 25,930,986 | `9acaede8d9b0a190489b49ebf38063bc69897c0d5f125c7549a6f7ee91a0b3c0` | 2026-10-19T18:13:18Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr18.fa.gz | reference/ucsc/chr18.fa.gz | 25,154,367 | `fa2077f5ebee2db6cc44df8e7e764c5147d95b840ed05b0a158d8f0b84581f14` | 2026-10-19T18:13:20Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr19.fa.gz | reference/ucsc/chr19.fa.gz | 17,916,986 | `e56423c5fb8d06fd34f6c9ddd7b7cb40aa97cd73c8f3e5b6a3a41ea4556cd4e8` | 2026-10-19T18:13:21Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr20.fa.gz | reference/ucsc/chr20.fa.gz | 20,350,590 | `271ca0ee4247c2fa30c8491764ad8acd4bdde8eb3cf314f0720235010ae85c9f` | 2026-10-19T18:13:22Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz | reference/ucsc/chr21.fa.gz | 12,709,705 | `c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b` | 2026-10-19T18:13:24Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz | reference/ucsc/chr22.fa.gz | 12,255,678 | `05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695` | 2026-10-19T18:13:25Z |
| reference | https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chrX.fa.gz | reference/ucsc/chrX.fa.gz | 49,662,430 | `1c7134f428960272a4b66baf53268aea5f6c756577b05bbab9af33c29b543685` | 2026-10-19T18:13:27Z |
| panel | https://www.ncbi.nlm.nih.gov/clinvar/docs/acmg/ | panel/acmg_sf_page.html | 74,807 | `c4ee73b2a773571b2f90c64e2a2b5a5471a3ead0b95c287c757e9e372863f53f` | 2026-10-19T18:21:24Z |
| panel | https://rest.ensembl.org/info/data/?content-type=application/json | panel/ensembl_info_data.json | 18 | `86e87c46ae1a424702676493d024d0508ce60f6c951b0b2803ce10269e09c20c` | 2026-10-19T18:21:25Z |
| panel | https://rest.ensembl.org/lookup/symbol/homo_sapiens (POST) | panel/ensembl_lookup.json | 35,956 | `507208a797be3329d817009c2f6f4c42b6c93f6b920625c9ddc822df895a4e80` | 2026-10-19T18:21:29Z |
| gnomad | https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chrN.vcf.bgz (region fetch) | gnomad/gnomad.genomes.v4.1.acmg_sf_panel.vcf.gz | 34,709,152 | `eebd1d875f3eed6e9d21540448dd29bd11eae7d56d3ed31ae5b9b68592189ffd` | 2026-10-19T18:26:08Z |

Derived file: `reference/hg38_selected.fa.gz` (chr1 to chr22 and chrX concatenated and bgzipped,
942,242,686 bytes, SHA-256 `461fca1af0f3fe4d526c5e1724554b643dbfb4d26bf68bdde2ebbea3f5a29c02`).

## Terms

Read at source on 2026-10-19:

- UCSC hg38 chromosomes: the folder README says "All the files in this directory are freely available for public use."
- NCBI (ClinVar, ACMG page): the NCBI policies page says NCBI "places no restrictions on the use or distribution of the data"; it also notes that some submitters may claim rights on their submissions.
- GIAB (NIST) on AWS: the registry entry (registry.opendata.aws/giab, managed by NIST) says "There are no restrictions on the use of this data."
- gnomAD: primary data are released under CC0 1.0 (gnomad.broadinstitute.org/policies); some annotations bundled with gnomAD, such as SpliceAI scores, carry their own terms. Only AC, AN, AF, nhomalt and AF_grpmax are used here.
- Ensembl: no restrictions on access to or use of its data; code under Apache 2.0; some third-party data distributed with Ensembl may carry their own constraints (mart.ensembl.org/info/about/legal/disclaimer.html). Only gene coordinates from the REST lookup are used here.

ClinVar's upload of 2026-10-12 is the file `clinvar_20261011.vcf.gz`
(`##fileDate=2026-10-11`, server timestamp 2026-10-12 22:23 UTC). The older release is
`clinvar_20251013.vcf.gz`, the archive release closest to 12 months earlier.
