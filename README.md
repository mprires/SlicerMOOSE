![Moose-logo](Images/moose.png)

## The official 3DSlicer Extension of MOOSE 3.0

MOOSE (Multi-organ objective segmentation) is a data-centric AI solution that generates multilabel organ segmentations to facilitate systemic TB whole-person research.

## Using the Extension
1. Find the extension in the `Segmentation` category and open it. 
2. When you use the extension the first time, only the `Install Dependencies` button will be enabled. Please click it to perform the initial setup of dependencies, which includes PyTorch and MOOSE.
   * For Windows users: Please make sure that the PyTorch extension is also installed. 
   * For Linux/Unix users: The PyTorch extension is not required, as native `torch` works in most cases. 
   * The installation will take a while, and it is normal that 3DSlicer might become unresponsive during the installation.
3. After a successful installation, the `Input Volume` and `Model` selector section will be enabled. 
4. Select a volume (which has to be a CT image) and a model and click on `Run Segmentation` and wait for the process to finish.
   * Our dataset consists mostly of total/whole body CT images. We **strongly** recommend to use only CT images with a similar field of view.
   * The `clin_ct_body_composition` model requires the L3 region of vertebrae to be in the field of view. If the model does not generate a segmentation, the field of view of the CT might be not suitable.
5. After the process finished, you will be able to select the segmentation and display/work with/modify it as you please.
   * The expected compute time of total/whole body CTs with a GPU is around 60 seconds.
   * With only CPU enabled, it might take up to 40 minutes.

## Available Segmentation Models 🧬

MOOSE 3.0 offers a wide range of segmentation models catering to various clinical and preclinical needs. Here are the models currently available:

| **Model Name**        | **Intensities and Regions**                                                                                                                                                                                                                           |
|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `clin_ct_cardiac`     | 1: heart_myocardium, 2: heart_atrium_left, 3: heart_atrium_right, 4: heart_ventricle_left, 5: heart_ventricle_right, 6: aorta, 7: iliac_artery_left, 8: iliac_artery_right, 9: iliac_vena_left, 10: iliac_vena_right, 11: inferior_vena_cava, 12: portal_splenic_vein, 13: pulmonary_artery|
| `clin_ct_digestive`   | 1: colon, 2: duodenum, 3: esophagus, 4: small_bowel                                                                                                                                                                  |                                                                                      
| `clin_ct_lungs`       | 1:lung_upper_lobe_left, 2:lung_lower_lobe_left, 3:lung_upper_lobe_right, 4:lung_middle_lobe_right, 5:lung_lower_lobe_right                                                                                                                             |
| `clin_ct_muscles`     | 1: autochthon_left, 2: autochthon_right, 3: gluteus_maximus_left, 4: gluteus_maximus_right, 5: gluteus_medius_left, 6: gluteus_medius_right, 7: gluteus_minimus_left, 8: gluteus_minimus_right, 9: iliopsoas_left, 10: iliopsoas_right                          |
| `clin_ct_organs`      | 1: adrenal_gland_left, 2: adrenal_gland_right, 3: bladder, 4: brain, 5: gallbladder, 6: kidney_left, 7: kidney_right, 8: liver, 9: lung_lower_lobe_left, 10: lung_lower_lobe_right, 11: lung_middle_lobe_right, 12: lung_upper_lobe_left, 13: lung_upper_lobe_right, 14: pancreas, 15: spleen, 16: stomach, 17: thyroid_left, 18: thyroid_right, 19: trachea |
| `clin_ct_peripheral_bones` | 1: carpal_left, 2: carpal_right, 3: clavicle_left, 4: clavicle_right, 5: femur_left, 6: femur_right, 7: fibula_left, 8: fibula_right, 9: fingers_left, 10: fingers_right, 11: humerus_left, 12: humerus_right, 13: metacarpal_left, 14: metacarpal_right, 15: metatarsal_left, 16: metatarsal_right, 17: patella_left, 18: patella_right, 19: radius_left, 20: radius_right, 21: scapula_left, 22: scapula_right, 23: skull, 24: tarsal_left, 25: tarsal_right, 26: tibia_left, 27: tibia_right, 28: toes_left, 29: toes_right, 30: ulna_left, 31: ulna_right |
| `clin_ct_ribs`        | 1: rib_left_1, 2: rib_left_2, 3: rib_left_3, 4: rib_left_4, 5: rib_left_5, 6: rib_left_6, 7: rib_left_7, 8: rib_left_8, 9: rib_left_9, 10: rib_left_10, 11: rib_left_11, 12: rib_left_12, 13: rib_left_13, 14: rib_right_1, 15: rib_right_2, 16: rib_right_3, 17: rib_right_4, 18: rib_right_5, 19: rib_right_6, 20: rib_right_7, 21: rib_right_8, 22: rib_right_9, 23: rib_right_10, 24: rib_right_11, 25: rib_right_12, 26: rib_right_13, 27: sternum |
| `clin_ct_vertebrae`   | 1: vertebra_C1, 2: vertebra_C2, 3: vertebra_C3, 4: vertebra_C4, 5: vertebra_C5, 6: vertebra_C6, 7: vertebra_C7, 8: vertebra_T1, 9: vertebra_T2, 10: vertebra_T3, 11: vertebra_T4, 12: vertebra_T5, 13: vertebra_T6, 14: vertebra_T7, 15: vertebra_T8, 16: vertebra_T9, 17: vertebra_T10, 18: vertebra_T11, 19: vertebra_T12, 20: vertebra_L1, 21: vertebra_L2, 22: vertebra_L3, 23: vertebra_L4, 24: vertebra_L5, 25: vertebra_L6, 26: hip_left, 27: hip_right, 28: sacrum |
| `clin_ct_body_composition`   | 1: skeletal_muscle, 2: subcutaneous_fat, 3: visceral_fat |

![Alt Text](/Images/MOOSE.gif)

## More on MOOSE
For more information, visit the package repository of [MOOSE](https://github.com/ENHANCE-PET/MOOSE).
There, you will find installation instructions for the CLI version and the package variant of MOOSE as well as licensing information.

## Citation
If you like MOOSE3.0, please cite it's original publication
>Shiyam Sundar LK, et al. Fully Automated, Semantic Segmentation of Whole-Body 18F-FDG PET/CT Images Based on Data-Centric Artificial Intelligence. Journal of Nuclear Medicine. 2022 Dec;63(12):1941-1948. doi:[10.2967/jnumed.122.264063 ](https://doi.org/10.2967/jnumed.122.264063 )

Also, please cite nnU-Net:
>Isensee F, et al. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. Nature Methods. 2021;18(2):203-211. doi:[10.1038/s41592-020-01008-z](https://doi.org/10.1038/s41592-020-01008-z)

## 🦌 MOOSE: A part of the [enhance.pet](https://enhance.pet) community

![Alt Text](/Images/Enhance.gif)