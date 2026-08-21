---
source_id: composite_pmc_9294053_impact_dataset
domain: composite
title: "Dataset for Surface and Internal Damage after Impact on CFRP Laminates"
url: https://pmc.ncbi.nlm.nih.gov/articles/PMC9294053/
license: "Creative Commons Attribution 4.0 International (CC BY 4.0)"
parser: jats-xml
source_sha256: 1994C62885AC9D2DC1A94B19E2E07C3CA0B9B895666D6CC547ACC41070DB010F
review_status: machine_parsed_pending_expert_review
---

# Dataset for surface and internal damage after impact on CFRP laminates

## Abstract

Various foreign objects can collide with CFRP structures, such as CFRP aircraft. Once something impacts with CFRP laminates, both surface damage and internal damage can occur. Even if the external damage is such invisible as called barely visible impact damage, there are matrix cracks or delamination that are the main cause of compressive strength reduction, so it is difficult to find the relationship between external and internal damage on CFRP laminates. This dataset is prepared for predicting impact information only from surface damage profiles using Machine Learning (Hasebe et al., 2022). It includes three data, surface damage image (png), surface depth contour image(png), and internal damage image after ultrasound C-scanning (jpg) after low-velocity impact testing under various impact conditions. The data are helpful for researchers and engineers who deal with the impact behavior of CFRP or data science.

## Data Description [sec0001a]

The data consists of the external damage image, surface depth contour plot and internal damage image of carbon fiber reinforced plastics (CFRP) after low-velocity impact (LVI) testing. The impact test was carried out using the Drop Tower Impact System CEAST 9350 (Instron Corporation) under various impact conditions (Fig. 1, Table 1). The specimens were put between two plates to fix (Fig. 2). Three specimens were prepared for each impact condition. After the LVI test, a wide area measurement system VR-5000 (Keyence Corporation) and the ultrasound C-scanning system HIS3 (KJTD Co., Ltd.) were utilized to measure external damage (Figs. 3 and 4). Fig. 5, Fig. 6, Fig. 7, Fig. 8, Fig. 9, Fig. 10, Fig. 11, Fig. 12 describe (a) Sample surface image, (b) depth contour plot, and (c) B scope and C scope as described in Table 1.Fig. 1Drop tower impact system CEAST 9350.Fig. 1Table 1Impact conditions.Table 1Specimen No.LaminatesImpactorsImpact energy [J/mm]Figure No.1, 2, 3C8 ([0/90]2s)HemiA3.3557, 8, 9C8([0/90]2s)Coni603.3562, 3, 40Q8([45/0/-45/90]s)HemiA3.3577, 8, 9Q8([45/0/-45/90]s)Coni603.3581, 2, 3C24([0/90]6s)HemiA3.3597, 8, 9C24([0/90]6s)Coni603.35101, 2, 25Q24([45/0/-45/90]3s)HemiA3.35117, 8, 9Q24([45/0/-45/90]3s)Coni603.3512Fig. 2How to fix the specimens : (a) image and (b) diagram.Fig. 2Fig. 3Wide-area 3D measurement system VR-5000.Fig. 3Fig. 4Ultrasound C-scanning system HIS3.Fig. 4Fig. 5(Top to bottom) Surface images, depth contour plot, and C-scanning of C8/HemiA.Fig. 5Fig. 6(Top to bottom) Surface images, depth contour plot, and C-scanning of C8/Coni60.Fig. 6Fig. 7(Top to bottom) Surface images, depth contour plot, and C-scanning of Q8/HemiA.Fig. 7Fig. 8(Top to bottom) Surface images, depth contour plot, and C-scanning of Q8/Coni60.Fig. 8Fig. 9(Top to bottom) Surface images, depth contour plot, and C-scanning of C24/HemiA.Fig. 9Fig. 10(Top to bottom) Surface images, depth contour plot, and C-scanning of C24/Coni60.Fig. 10Fig. 11(Top to bottom) Surface images, depth contour plot, and C-scanning of Q24/HemiA.Fig. 11

All dataset can be found in Mendeley Data[2], [3], [4], [5], [6], [7], [8], each separated by layups and specimen size (C8, C16, C24, Q8, Q16, Q24, and ASTM specimens). Each Mendeley data consists of1.”Impacted surface image” folder2.”Internal damage” folder3.”Non-impacted surface image” folder4.”Surface profile” folder5.”Impact condition” file

”Impacted surface image” folder contains the images off impacted surface, which are the outputs of VR-5000. In ”Internal damage” folder, the screenshots of the c-scanning result are stored. In ”non-impacted surface image” folder, the opposite surface images of those in ”impacted surface image” folder are saved. Data in ”Surface profile” folder is the out-of-plane displacement of impacted surface before and after the impact test. It is able to duplicate the depth contour plots in Fig. 5, Fig. 6, Fig. 7, Fig. 8, Fig. 9, Fig. 10, Fig. 11, Fig. 12 using these data. Also, all data in the related paper[1] is based on these surface profile data. ”Impact condition.xlsx” explains each impact condition of the Mendeley data.Fig. 12(Top to bottom) Surface images, depth contour plot, and C-scanning of Q24/Coni60.Fig. 12

## Experimental Design, Materials and Methods [sec0002a]

### Material and Specimens [sec0001]

This research experimented with T800S/3900-2B, an interface toughened material manufactured by Toray Industries Inc. Although the material properties are not evalated in this study, the previous research conducted various experiments to collect them [9]. The size of the specimen was cut into 80mm×80mm from large plates.

### Low-Velocity Impact Test [sec0002]

The testing machine, CEAST 9350 (Fig. 1) confirms to ASTM D7136[10], and the followings were arranged for this experiment [1]:•The specimen size (see 1)•The fixing tools (see Fig. 2)•The impactor shapes•The impact energy : The energy is calculated using the specimen thickness. Since the mass of the impactor is known, the initial height is obtained.

To reproduce these data, put the specimen on the center of fixing tools. Otherwise, the boundary condition lacks uniformity. Table 1 lists the impact conditions (the stacking sequence, the impactor shape and the impact energy) of the data which is mentioned in this paper. The ply thickness is about 0.1875 mm.

### Surface Damage Measurement [sec0003]

The software attached to VR-5000 (Fig. 3) was used to analyze the raw surface profile data whose extension is unique to them (.zon). As the first step of the analysis, it is necessary to define a reference plane (i.e., undeformed intact surface) based on the mean-square fitting from four corners of each specimen. Here, the relative positions of four corners are considered to be consistent before and after the LVI test since all of the four edges were fixed during the test. After defining the reference plane, the software calculates each depth on the specimen. Then, it is able to obtain each depth contour plot in Fig. 5, Fig. 6, Fig. 7, Fig. 8, Fig. 9, Fig. 10, Fig. 11, Fig. 12. This software considers the bulge direction to be positive.Each impact condition is summarized in Table 1.

### Internal Damage Measurement [sec0004]

In order to evaluate the internal damage of the impacted specimen, ultrasound C-scanning was conducted (Fig. 4). Table 2 lists the measurement configuration of C-scanning. As the software cannot export raw file in a non-proprietary format, the screenshot was taken as image data. In Fig. 5, Fig. 6, Fig. 7, Fig. 8, Fig. 9, Fig. 10, Fig. 11, Fig. 12, the C-scanning data of the same impact damage are also shown. The color represents the amplitude level.Table 2Ultrasound c-scanning measurement conditions.Table 2ParameterValueProbe3.5 MHzScanning pitch0.200 mm x 0.200 mmScanning length75.000 mm x 75.000 mm

## CRediT authorship contribution statement [sec0004a]

Saki Hasebe: Methodology, Investigation, Writing – original draft. Ryo Higuchi: Conceptualization, Writing – review & editing. Tomohiro Yokozeki: Supervision. Shin-ichi Takeda: Validation, Supervision.

## Declaration of Competing Interest

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.
