---
source_id: composite_nasa_tm_2014_218545
domain: composite
title: "Nondestructive Evaluation for Inspection of Composite Sandwich Structures"
url: https://ntrs.nasa.gov/citations/20150001252
parser: pdftotext-layout
source_sha256: 29888B077DCF7047630C589BB8E74FF11A704B440DA32625351F2586CC3FEE8D
review_status: machine_parsed_pending_expert_review
---

# Nondestructive Evaluation for Inspection of Composite Sandwich Structures

## Page 5

                                       Abstract

    Composite honeycomb structures are widely used in aerospace applications due to
their low weight and high strength advantages. Developing nondestructive evaluation
(NDE) inspection methods are essential for their safe performance. Flash thermography
is a commonly used technique for composite honeycomb structure inspections due to its
large area and rapid inspection capability. Flash thermography is shown to be sensitive
for detection of face sheet impact damage and face sheet to core disbond. Data
processing techniques, using principal component analysis to improve the defect
contrast, are discussed. Limitations to the thermal detection of the core are investigated.
In addition to flash thermography, X-ray computed tomography is used. The aluminum
honeycomb core provides excellent X-ray contrast compared to the composite face
sheet. The X-ray CT technique was used to detect impact damage, core crushing, and
skin to core disbonds. Additionally, the X-ray CT technique is used to validate the
thermography results.




                                   Nomenclature


V      = temperature
l      = thickness
K      = thermal conductivity
f      = heat flux
α            
            




                                                1

## Page 6

                                     Introduction
    Composite honeycomb structures continue to be used widely in aerospace
applications due to low weight and high strength requirements. There is a growing
interest in the application of thermal methods for nondestructive evaluation (NDE) of
composite sandwich structures [1-3]. Some of the advantages of thermal NDE are
noncontact, rapid, capable of imaging large areas, applicable to complex geometries,
and quantitative. The technique is safe where only a small amount of heat is applied to
the surface of the structure. Thermography has shown good potential for detection of
various defects in composite structures. Defects such as delaminations, disbonds, gross
porosity, and fiber volume fraction variations are detectable using thermography. X-ray
computed tomography (CT) is also used to detect defects in sandwich structures [4].
The X-ray CT inspection results provide a true volumetric measurement of the damage,
however the inspection must be performed within a radiation enclosure. The aluminum
honeycomb core provides excellent X-ray contrast compared to the composite face
sheets and therefore, is an ideal inspection technique. The X-ray system is used to
detect impact damage, core crushing, and skin to core disbonds.

    Specific to composite honeycomb structures, face sheet delaminations, face sheet to
core disbonds, and core crushing are defects of interest. Typically the composite face
sheets are relatively thin compared to the overall thickness and therefore, thermography
is effective for detection of face sheet delaminations. Detection of the face sheet to core
disbonds is also critical. Under load, face sheet to core disbonds can grow leading to
disbond buckling failure which can lead to catastrophic structural failure [5]. Both
thermography and X-ray CT have the potential to detect face sheet to core disbonds.
The thermal detection limitations of face sheet to core disbonds are investigated using
analytical and finite element thermal modeling.

     Flash thermography results are presented on composite honeycomb samples with
face sheet delaminations, face sheet to core disbonds, and core crushing. The thermal
results are compared to the X-ray CT measurements. Thermal modeling is used to
optimize the inspection. The thermal modeling consisted of a 1-dimensional (1-D)
analytic model and 2-dimensional (2-D) finite element model. The 1-D analytical model
is used to provide an understanding of the effect of the adhesive between the face sheet
and core. The 2-D finite element model is used for two purposes: first to determine the
optimal thermal processing parameters for detection of face sheet delamination damage
and face sheet to core disbonds and second to determine the thermal detection
limitations caused by the face sheet to core thickness ratio. This model is also used for
differentiating between impact damage and face sheet disbonds using early time and
late time analysis. X-ray CT is used to image the skin to core disbond and impact
damage areas by viewing averaged image data through-the-thickness. The core
crushed areas are detected by measuring the deviation of the core away from the non-
damaged side.


                                Sample Configuration

    The configuration of the composite sandwich samples studied is shown in Figure 1.
The sandwich structure is comprised of an aluminum hexagonal core with outer graphite
plain weave composite face sheets. The core thickness is 2.54 cm and the composite
face sheet thickness is approximately 0.1 cm. The core cell wall thickness is

                                                 2

## Page 7

approximately 0.02 cm with a cell size of 0.32 cm. The ratio of the face sheet to core wall
thickness is 5 to 1.




        Figure 1. Typical configuration of composite face sheet with aluminum core.


                                Flash Thermography
    Thermographic single side flash inspection data were acquired using a commercially
available thermal inspection system. The thermal inspection system uses two flash
lamps that are mounted within a hood to contain the flash, as shown in Figure 2. The
flash power is provided from two power supplies delivering 4.8 kJ of energy to the flash
tubes. The flash duration is typically less than 10 milliseconds and is instantaneous
compared to the frame rate of the camera and the thermal response time of the
composite [6]. An infrared camera was used to record the surface temperature
response. The camera operates in the mid infrared band with a pixel resolution of
640x512. The camera sensitivity or noise equivalent temperature difference, quoted by
the manufacturer, is less than 0.02 Kelvin. The camera is configured with a 25 mm
germanium optical lens. The data were acquired at 60 Hz for 720 frames. The total
acquisition time was 12 seconds.




        Figure 2. Thermal inspection system with flash lamps contained in hood.

                                  Thermal Modeling
    The thermal modeling efforts included a 1-D approach to investigate the effects of
the adhesive between the face sheet and core. A multi-layer 1-D thermal model was
used by comparing the difference in the thermal response between the face sheet
bonded directly to the core and a thin layer of adhesive between the face sheet and
core. From these results, a 2-D finite element model was configured similar to the right

                                                3

## Page 8

image of Figure 3 using a “T” configuration. This was used to study the effect of the
lateral heat flow in reducing thermal contrast for imaging a core disbond. Simulated
camera noise, determined from actual thermal data, was added to the model results. An
X-ray CT image showing the aluminum core bonded to a composite face sheet is shown
in the left image of Figure 3. For both of these models, the fillet bonds between the core
and adhesive along the length of the core wall were not considered.




      Figure 3. X-ray CT image (left) showing actual thermal configuration of attached core
      to the face sheet and thermal model configuration (right).

1-D Modeling
    The 1-D analytical model provided an understanding of the effect of the adhesive
between the face sheet and core and is given in equation (1) [7]. The multilayered
model includes the face sheet composite layer, the adhesive layer and the core layer. A
contrast function is defined by the temperature difference response to impulse flux
heating at the surface between points A, B, and C as shown in Figure 3. For point A, the
1-D analytical model contains 3 layers: the face sheet, the adhesive, and the core,
equation (1). For points B and C the analytical model contains 1 layer (face sheet layer
only) and 2 layers (face sheet and the core), equations (2) and (3) respectively. The
equations are given below as:

       ⎡                            1                     ⎤⎡           1adhesive ⎤ ⎡                          1                   ⎤
⎡v ⎤ ⎢cosh [ q 2 l2 ]         -          sinh [ q 2 l2 ] ⎥ ⎢1     -              ⎥ ⎢cosh [ q1 l1 ]     -          sinh [ q1 l1 ] ⎥ ⎡v A⎤
   l
                                      q                               K adhesive ⎥ ⎢                            q                            (1)
⎢ ⎥ ⎢=                          K core 2                  ⎥⎢                                             K comp 1                 ⎥ ⎢⎢ ⎥⎥
                                                                                                                  cosh [ q1 l1 ] ⎥⎦ ⎣f 1 ⎦
⎣ 0⎦ ⎢                                                                             ⎢
       ⎣-K core q 2 sinh [ q 2 l2 ]      cosh [ q 2 l2 ] ⎥⎦ ⎢⎣0       1          ⎥
                                                                                 ⎦ ⎣-K comp q1 sinh [ q1 l1 ]



                                            ⎡                      1                     ⎤
                                     ⎡v ⎤ ⎢cosh [ q1 l1 ]    -           sinh [ q1 l1 ] ⎥ ⎡v B⎤
                                     ⎢ 2⎥ = ⎢                  K comp q1                                                                     (2)
                                                                                         ⎥ ⎢⎢ ⎥⎥
                                     ⎣0⎦ ⎢
                                             - K  q
                                            ⎣ comp 1 sinh [ q  l
                                                             1 1 ]       cosh  [ q  l
                                                                                  1 1  ] ⎥⎦ ⎣f 1 ⎦


                          ⎡                          1                     ⎤ ⎡                        1                    ⎤
                   ⎡v ⎤ ⎢cosh [ q 2 l2 ]       -          sinh [ q 2 l2 ] ⎥ ⎢cosh [ q1 l1 ]     -          sinh [ q1 l1 ] ⎥ ⎡v C⎤
                   ⎢ 3⎥ = ⎢                            q                                                q                                    (3)
                                                 K core 2                  ⎥ ⎢                    K comp 1                 ⎥ ⎢⎢ ⎥⎥
                   ⎣0⎦ ⎢
                           -      q
                          ⎣ K core 2 sinh [ q 2 2l ]      cosh  [ q   l
                                                                    2 2  ] ⎥ ⎢-      q
                                                                           ⎦ ⎣ K comp 1 sinh [ q  l
                                                                                                1 1 ]      cosh  [ q  l
                                                                                                                    1 1  ] ⎥⎦ ⎣f 1 ⎦




                                                                             s                           s
                                                  where q 1 =                         and q 2 =
                                                                         α comp                       α core
                                                                                                                .



                                                                                  4

## Page 9

     The model can be solved analytically in the Laplace domain [8] where VA, VB and VC
are the 3 layer, 1 layer, and 2 layer surface temperature responses in the Laplace
domain respectively, f1 is the instantaneous heat flux input estimated to be
approximately 1 cal/cm2 [9], l1 is the face sheet composite layer thickness = 0.1cm, l2 is
the core layer thickness = 2.54 cm, Kcomp is the composite thermal conductivity = 0.0021
cal/cm sec oC, Kaluminum is the aluminum thermal conductivity = 0.33 cal/cm sec oC, acore is
the composite thermal diffusivity = 0.004 cm2/sec, aaluminum is the aluminum thermal
diffusivity = 0.53 cm2/sec, Kadhesive is the adhesive thermal conductivity = 0.0006 cal/cm
sec oC, ladhesive is the estimated adhesive thickness = 0.001 cm [10], and s is the Laplace
complex argument. The temperature results are normalized before taking the difference.
The results are shown in Figure 4 where the contrast between the model with adhesive
and no adhesive (VA – VC) is plotted. In addition, the difference between the face sheet
only and face sheet and core (VB – VC) is plotted for the core contrast. Compared to the
core contrast the adhesive difference response is minimal.




   Figure 4. 1-D model temperature difference of adhesive and no adhesive compared
   to face sheet and face sheet and core.

2-D Finite Element Modeling
    The 2-D finite element method (FEM), via a commercially available software package
[11], was used to determine the thermal detection limitations caused by the face sheet to
core thickness ratio. The face sheet thickness to core thickness ratios studied were 4:1,
5:1, 6:1, 7:1 and 8:1. These models were simplified using the face sheet bonded directly
to the core (no adhesive) based on the 1-D results. An example finite element analysis
model of a composite face sheet with aluminum core is shown in Figure 5. The 2-D
model contains 1038 elements and 620 nodes. The face sheet thickness is 0.1 cm and
the aluminum core cell wall thickness is 0.02 cm. The ratio of the face sheet to core
thickness is 5:1. The width of the face sheet is 0.5 cm and the length of the core is 0.4
cm, as shown in Figure 5. The surface temperature (room temperature subtracted) as a
function of time is also shown in Figure 5 (right plot). For early times around 0.3
seconds there is no contrast caused by the core. This reveals that defects within the
face sheet can be detected around this time and therefore can be differentiated from
core defects. Later in time, around 0.97 seconds, the aluminum core lowers the
temperature at the face sheet surface over the core. The temperature contrast fades
away around 8.3 seconds. Figure 6 shows a comparison between the 2-D FEM and the
1-D analytical model results. For early times up to around 0.75 seconds, there is fairly
good agreement between the 2 models. Past 0.75 seconds the models diverge and as
expected the 2-D model would predict lower temperature contrast since the lateral heat
flow is taken into account. Comparisons to 2-D model results, with camera noise
added, of the contrast evolution vs. time for various face sheet to core cell wall thickness
ratios are shown in the right plot of Figure 6. The temperature difference was calculated

                                                 5

## Page 10

by subtracting a point over the core from a point away from the core. The core wall
thickness is 0.020 cm and the thickness of the face sheet values are 0.08, 0.10, 0.12,
0.14, and 0.16 cm, resulting in face sheet thickness to core thickness ratios of 4:1, 5:1,
6:1, 7:1 and 8:1 respectively. The temperature difference is barely above the noise for
the 8:1 ratio configuration indicating a face sheet to core disbond would not be
detectable.




   Figure 5. Finite element model of a composite face sheet with aluminum core (left
   image) and corresponding surface temperature evolution (right plot).




   Figure 6. Contrast evolution comparison of 2-D finite element model comparison to
   1-D analytical model (left plot) and temperature difference comparison of face sheet
   to core cell wall thickness ratios (right plot).


                                    Data Processing

    Principal component analysis (PCA) is common for processing of thermal data
[12,13]. This algorithm is based on decomposition of the thermal data into its principal
components or eigenvectors. Singular value decomposition is a routine used to find the
singular values and corresponding eigenvectors of a matrix. Since thermal NDE signals
are slowly decaying waveforms, the predominant variations of the entire data set are
usually contained in the first or second eigenvectors, and thus account for most of the
data variance of interest. The PCA is computed by defining a data matrix A, where the
time variations are along the columns and the spatial image pixel points are row-wise.
The matrix A is adjusted by subtracting the mean along the time dimension. The matrix
A can then be decomposed using singular value decomposition as:

                                                 6

## Page 11

                                       T           2     T
                                     A A = U* Γ * U                                 (4)

where Γ is a diagonal matrix containing the squares of the singular values and U is an
orthogonal matrix, which contains the basis functions or eigenvectors describing the time
variations. The eigenvectors can be obtained from the columns of U. The PCA image is
calculated by dot product multiplication of the selected eigenvector times the
temperature response (data matrix A), pixel by pixel. Typically the first or second
eigenvector PCA image provides good contrast for defect detection. The first
eigenvector is dominated by the transient cool down of the face sheet layer and is more
suited for early time detection of face sheet delamination. The second eigenvector is
less dominant and defines the temporal contrast evolution of the face sheet bonded to
the core. This is shown in Figure 7 where the 2nd eigenvectors, determined from the 2-D
model data for each of the thickness to core ratios, are plotted for comparison (no
camera noise added). The maximum contrast point moves later in time due to the
increases in the face sheet thickness, as expected. This indicates the 2nd eigenvector is
the best candidate for imaging the face sheet to core disbond regions. Also the
maximum contrast time determined from the 2nd eigenvectors are different compared to
the maximum time determined from the difference calculation with no camera noise
added (see Table 1 in Figure 7). While both agree that with increasing face sheet
thickness the maximum point moves slightly later in time; the maximum contrast time
determined from the 2nd eigenvector is more accurate because all the surface points are
used from the model instead of only the 2 surface points used in the difference
calculation. Also shown in Figure 7, the 8:1 ratio eigenvector curve does not have a
clear maximum point, thus indicating the core response is not as dominant in the data
and cannot be detected as confirmed by the 8:1 ratio temperature difference plot in
Figure 6 (especially with camera noise added).




   Figure 7. 2nd Eigenvectors determined from the 2-D FEM results (left plot) and table
   of maximum contrast times determined from temperature difference calculations
   (from Figure 6) and the local maximum contrast time from 2nd eigenvector
   calculations.


                 X-ray Computed Tomography (CT) System
The advanced micro-focus X-ray system used in this study is shown in Figure 8. This
system is capable of resolving details down to 5 microns, and with magnifications up to



                                               7

## Page 12

          Figure 8. X-ray CT system used for sandwich structure inspections.


160 times. The X-ray source voltage can be varied from 25 to 225 kilovolts. The
detector array size is 2,000 x 2,000 with a 200µ pitch. The sample can be manipulated
with 5 axes of freedom, while continuously viewing the image on a monitor. Defects can
be rapidly located, zooming in for detailed analysis. The system is contained in a
radiation enclosure, with X-ray, manipulator and imaging controls housed in a separate
control console. Sample sizes can range up to 25.4 x 25.4 cm.


                Comparison of Thermography to Computed
                           Tomography X-ray

    Based on the 2-D modeling results from sections 3.2 and 4.1, an early time window
can be used for detection of defects within the composite face sheet. A late time window
can be used to detect a face sheet to core disbond. Shown in Figure 9 is an early time
(0.33 – 1.5 seconds) PCA image of a composite honeycomb sample with impact
damage delamination defects (7 total impacts). The impact damage shows up as lighter




   Figure 9. Photograph of impacted sandwich structure (left image) and early time
   thermography inspection results (middle image) along with X-ray CT (right images).

                                               8

## Page 13

regions. The X-ray CT images show the core still attached to the face sheet with some
core crushing. The PCA image was calculated from the first eigenvector. A comparison
of the early time and late time (1.5 – 8.3 seconds) PCA images to X-ray CT inspection
images are shown in Figure 10. There is good qualitative agreement between the
thermography inspection image (early time analysis) compared to the X-ray CT image
for detection of impact damage. Figure 11 shows the areas of crushed core using X-ray
CT. The crushed core areas are determined by locating the core edges just below the
back face sheet and following the edges toward the front surface until they deviated by
three pixels from a linear fit and then traced back to a one pixel deviation; there are
minor core deformations deeper into the core that are ignored. The crushed core areas,
as shown in Figures 9 and 11, are not detectable with thermography.




   Figure 10. Thermography inspection results of early time (left image) and late time
(middle image) of an impacted sandwich structure along with X-ray CT (right image).




               Figure 11. Images of the core crushed areas using X-ray CT.


    Another sample, containing a face sheet crack, impact damage and core damage
(cut core) was inspected. Shown in Figure 12 is an early time (0.33 – 1.5 seconds) PCA
image of the honeycomb sample with a face sheet crack and impact damage defects.
The bottom left image of Figure 12 is the late time (5.0 – 8.3 seconds) PCA image of the
honeycomb sample showing the face sheet to core disbonds along the edge. A later

                                               9

## Page 14

start time (5.0 seconds) was used in the PCA processing to image the cut core areas
and this was found to provide optimal results. The later time requirement is most likely
due to some portion of the aluminum core still attached to the face sheet. This can be
clearly seen in the left X-ray CT images of Figure 13 where some of the cut core is still
attached to the face sheet and therefore later times were required to produce the surface
temperature contrast. The attached core along with the resin fillet bonding changes the
thermal response of the face sheet (more thickness) thus requiring a later start time to
reveal contrast. Shown in Figure 13 is a close up area of the boxed region of Figure 12
where the impact damage is over an area of cut core. The early time image and late
time image (shown in Figure 13) clearly reveals the face sheet impact damage and the
face sheet to core disbond respectively. The face sheet to core disbond region is larger
than the impact damage. The cut core cannot be detected under the impact damage
area, as expected due to the delamination blocking the heat flow.




   Figure 12. Thermography inspection results (early and late time) of the damaged
   sandwich panel with X-ray CT showing skin to core disbond.


                                       Summary
    Flash thermography and X-ray CT was used to detect defects in composite sandwich
structures with an aluminum core. A thermal method was presented to detect damage in


                                               10

## Page 15

aluminum core composite face sheet sandwich structures using PCA and time window
analysis. The early time window PCA image using the first eigenvector was applied to
detect face sheet impact damage. The late time window PCA image using the second
eigenvector was applied to detect the face sheet to core disbond areas. The FEM
analysis was helpful in selecting the eigenvector number and determining the optimal
time windows. The flash thermography technique was not able to detect the core
crushed areas. The X-ray CT inspection was able to detect impact damage, core
crushed areas, and skin to core disbonds. The flash thermography results compared
well with X-ray CT for impact damage detection and skin to core disbonds.




   Figure 13. Thermography inspection close up of impact damage over cut core with
   X-ray CT.



                                       References

   1. Sfarra, S. et al, “A comparative investigation for the nondestructive testing of
      honeycomb structures by holographic interferometry and infrared
      thermography“,J. Phys.: Conf. Ser. 214 012071, (2010).

   2. Clemente Ibarra-Castrando, et al, “Comparative Study of Active Thermography
      Techniques for the Nondestructive Evaluation of Honeycomb Structures”,
      Research in Nondestructive Evaluation Volume 20, Issue 1, (2009).

   3. Genest, M., Brothers, M., Beltempo, C. A., Rutledge, R. S., “Nondestructive
      Evaluation of Aluminum Honeycomb Sandwich Structures”, NATO Unclassified,
      STO-MP-AVT-224, (2013).

   4. Liu, Tong, Malcolm, Andrew A., and Xu, Jian, “High Resolution X-ray CT
      Inspection of Honeycomb Composites Using Planar Computed Tomography
      Technology”, 2nd International Symposium on NDT in Aerospace (2010).



                                                11
