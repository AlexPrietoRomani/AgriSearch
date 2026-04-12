---
agrisearch_id: 8b681884-819a-4f86-9c7a-2ebb9343e01e
doi: 10.1007/s10462-023-10466-8
title: 'Deep learning modelling techniques: current progress, applications, advantages,
  and challenges'
authors: Shams Forruque Ahmed, Md. Sakib Bin Alam, Maruf Hassan, Mahtabin Rodela Rozbu,
  Taoseef Ishtiak, Nazifa Rafa, M. Mofijur, A. B. M. Shawkat Ali, Amir H. Gandomi
year: 2023
journal: Artificial Intelligence Review
keywords: []
source_database: test
parser_engine: markitdown
---

University of Arkansas, Fayetteville
University of Arkansas, Fayetteville
ScholarWorks@UARK
ScholarWorks@UARK

Electrical Engineering and Computer Science
Undergraduate Honors Theses

Electrical Engineering and Computer Science

5-2025

Multimodal Learning for Visual Perception and Robotic Action
Multimodal Learning for Visual Perception and Robotic Action

Taisei Hanyu
University of Arkansas, Fayetteville, thanyu@uark.edu

Follow this and additional works at: https://scholarworks.uark.edu/elcsuht

 Part of the Artificial Intelligence and Robotics Commons

Click here to let us know how this document benefits you.

Citation
Citation
Hanyu, T. (2025). Multimodal Learning for Visual Perception and Robotic Action. Electrical Engineering
and Computer Science Undergraduate Honors Theses Retrieved from https://scholarworks.uark.edu/
elcsuht/19

This Thesis is brought to you for free and open access by the Electrical Engineering and Computer Science at
ScholarWorks@UARK. It has been accepted for inclusion in Electrical Engineering and Computer Science
Undergraduate Honors Theses by an authorized administrator of ScholarWorks@UARK. For more information,
please contact uarepos@uark.edu.

Multimodal Learning for Visual Perception and Robotic Action

Multimodal Learning for Visual Perception and Robotic Action

A thesis submitted in partial fulfillment
of the requirements for the degree of
Bachelor of Science in Computer Science

By

Taisei Hanyu
Department of Electrical Engineering and Computer Science
College of Engineering

May 2025
University of Arkansas

This thesis is approved for recommendation to the Honors College

Ngan Le, Ph.D.
Thesis Director:

Chase Rainwater, Ph.D.
Committee member

Roy A. McCann, Ph.D.
Committee member

Anthony Gunderman, Ph.D.
Committee member

Gianfranco Doretto, Ph.D.
Committee member

Abstract

Multimodal learning aims to weave information from images, language,

depth, and other sensors into one coherent representation, much as people nat-

urally combine sight, speech, and sound. Progress toward that goal is slowed

by three gaps: vision encoders that cannot balance crisp object boundaries with

global context, 3-D semantic maps that are computationally prohibitive for real-

time, open-vocabulary queries, and vision-language-action pipelines that depend

on large token pools with weak relational grounding.

We first introduce AerialFormer, a lightweight hybrid of convolutional and Trans-

former layers that captures long-range structure without sacrificing fine detail. On

the large-scale iSAID benchmark it reaches 69.3 % mean IoU, improving on the

previous best by 2.1 points, and it also surpasses recent methods on Potsdam and

LoveDA without extra computation.

We then introduce Open-Fusion, a real-time 3D semantic mapping system that

incrementally builds a TSDF volume using region-level features extracted from a

vision-language model. By storing open-vocabulary semantic embeddings in spa-

tial memory, it enables interactive and language-driven queries such as locating

objects directly from the 3D map, providing a practical foundation for semantic

understanding in robotic environments.

Finally, we propose SlotVLA, a relation-centric visual tokenizer and policy that

compresses each observation into a compact set of four interaction-focused slots,

explicitly capturing functional object relationships. On ten LIBERO-Goal manip-

ulation tasks, SlotVLA achieves 63 % success with a single camera and 75 % when

a wrist camera is added, an improvement of 4 to 11 points over object-centric or

pooled-token baselines while sustaining 12–15 fps inference.

These three contributions show that explicit structural bias, language-aligned 3-D

semantics, and compact relational tokens can make multimodal perception and

reasoning both faster and more accurate, offering a solid foundation for future

work on understanding complex environments across space, time, and modality.

THESIS DUPLICATION RELEASE

I hereby authorize the University of Arkansas Libraries to duplicate this thesis

when needed for research and/or scholarship.

Agreed

Refused

Taisei Hanyu

Taisei Hanyu

ACKNOWLEDGEMENTS

I would like to express my sincere gratitude to Dr. Ngan Le for her guid-

ance, support, and encouragement throughout my undergraduate research. Her

mentorship was instrumental not only in shaping the direction and outcomes of

this paper but also in influencing my overall research trajectory. I am truly grate-

ful for her incredible passion for computer vision and her unwavering dedication

to her students.

I also wish to thank my committee members—Dr. Chase Rainwater, Dr.

Roy A. McCann, Dr. Anthony Gunderman, and Dr. Gianfranco Doretto—for

their thoughtful feedback and encouragement.

I deeply appreciate the opportunity to work with my lab-mates—Kashu

Yamazaki, Minh Tran, Khoa Vo, and Thang Pham—and with my research collab-

orators, Nhat Chung, Huy Le, and Tung Kieu. I have learned a great deal from

each of them, and their contributions have enriched this work.

Finally, I am grateful to the faculty and staff of the Computer Science

and Computer Engineering (CSCE) Department at the University of Arkansas for

providing me with the opportunity to pursue my education in computer science.

Their instruction and support have played a key role in my academic development,

and I am thankful for the experiences and knowledge gained during my time here.

iv

TABLE OF CONTENTS

Abstract . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

Acknowledgements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

Table of Contents . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

ii

iv

v

List of Figures

. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . vii

List of Tables . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . viii

1 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
1.1 Architectural Advances in Visual Feature Extraction . . . . . . . .
. . . . . . . . . . . . . . . . . . . . . .
1.2 Contributions of the Thesis

2 Multi-Resolution Transformer for Aerial Image Segmentation . . . . . . .
2.1
INTRODUCTION . . . . . . . . . . . . . . . . . . . . . . . . . . .
2.2 RELATED WORKS . . . . . . . . . . . . . . . . . . . . . . . . . .
2.2.1 DL-Based Image Segmentation . . . . . . . . . . . . . . . .
2.2.2 Aerial Image Segmentation . . . . . . . . . . . . . . . . . . .
2.3 METHODOLOGY . . . . . . . . . . . . . . . . . . . . . . . . . . .
2.3.1 Network Overview . . . . . . . . . . . . . . . . . . . . . . .
2.3.2 CNN Stem . . . . . . . . . . . . . . . . . . . . . . . . . . . .
2.3.3 Transformer Encoder . . . . . . . . . . . . . . . . . . . . . .
2.3.4 Multi-Dilated CNN Decoder . . . . . . . . . . . . . . . . . .
2.3.5 Loss Function . . . . . . . . . . . . . . . . . . . . . . . . . .
2.4 EXPERIMENTS . . . . . . . . . . . . . . . . . . . . . . . . . . . .
2.4.1 Datasets . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
2.4.2 Evaluation Metrics . . . . . . . . . . . . . . . . . . . . . . .
2.4.3
Implementation Details . . . . . . . . . . . . . . . . . . . . .
2.4.4 Quantitative Results and Analysis . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . .
2.4.5 Qualitative Results and Analysis
2.5 DISCUSSION . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
2.6 CHAPTER CONCLUSION . . . . . . . . . . . . . . . . . . . . . .

3 Real-time Open-Vocabulary 3D Mapping and Queryable Scene Represen-

tation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
3.1
INTRODUCTION . . . . . . . . . . . . . . . . . . . . . . . . . . .
3.2 RELATED WORKS . . . . . . . . . . . . . . . . . . . . . . . . . .
. . . . . . .

3.2.1 Vision-Language Foundation Models (VLFMs).

1
2
3

6
6
9
10
11
13
13
14
15
19
22
22
22
24
25
26
38
45
46

47
47
49
49

v

3.2.2 Queryable scene representation.

. . . . . . . . . . . . . . . .
3.3 METHODOLOGY . . . . . . . . . . . . . . . . . . . . . . . . . . .
3.3.1 Problem Setup . . . . . . . . . . . . . . . . . . . . . . . . .
3.3.2 Region-based Feature Extractor . . . . . . . . . . . . . . . .
3.3.3 Real-time 3D Scene Reconstruction with Semantics . . . . .
3.3.4 Querying Semantics from the 3D Map . . . . . . . . . . . .
3.4 EXPERIMENTS . . . . . . . . . . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . .
3.4.1 Quantitative Benchmarks
3.4.2 Qualitative Results . . . . . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
3.4.3 Real-World Experiment
3.5 CHAPTER CONCLUSION & DISCUSSION . . . . . . . . . . . . .

4.2.1 VLA Learning in Robotic Manipulation.
4.2.2 Vision Token Reduction.

4.3.1 Low-Token Visual Representations
4.3.2 Limitations of Naive Reduction Strategies

4 Language-Guided Active Mapping for Robotic Manipulation . . . . . . .
4.1
INTRODUCTION . . . . . . . . . . . . . . . . . . . . . . . . . . .
4.2 RELATED WORKS . . . . . . . . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
4.3 PROBLEM FORMULATION . . . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . .
. . . . . . . . . .
4.4 METHODOLOGY . . . . . . . . . . . . . . . . . . . . . . . . . . .
Slot-Based Visual Tokenization . . . . . . . . . . . . . . . .
4.4.1
4.4.2 Task-Centric Multimodal Decoder . . . . . . . . . . . . . . .
4.4.3 LLM Action Decoding . . . . . . . . . . . . . . . . . . . . .
4.5 EXPERIMENTS . . . . . . . . . . . . . . . . . . . . . . . . . . . .
4.5.1 Experimental Setup . . . . . . . . . . . . . . . . . . . . . . .
4.5.2 Main Results
. . . . . . . . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . . . . . . . . . .
4.5.3 Ablations
4.6 CHAPTER CONCLUSION . . . . . . . . . . . . . . . . . . . . . .

5 Conclusions and Future Work . . . . . . . . . . . . . . . . . . . . . . . .
5.1 Conclusions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
5.2 Future Work . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

51
52
52
53
54
58
58
59
60
60
63

64
64
67
67
68
69
69
69
71
72
75
75
77
77
78
79
81

83
83
84

Bibliography . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

85

vi

LIST OF FIGURES

Figure 2.1: Examples of challenging characteristics in remote sensing image

segmentation . . . . . . . . . . . . . . . . . . . . . . . . . . . .
Figure 2.2: Overall network architecture of the proposed AerialFormer . . .
Figure 2.3:
Illustrations of the CNN Stem . . . . . . . . . . . . . . . . . . .
Figure 2.4: The figure illustrates a Transformer Encoder Block . . . . . . .
Figure 2.5: An illustration of the MDC Block . . . . . . . . . . . . . . . . .
Figure 2.6: The qualitative ablation study on the CNN Stem and multi-

dilated CNN decoder . . . . . . . . . . . . . . . . . . . . . . . .
Figure 2.7: Foreground–background imbalance comparison . . . . . . . . .
Figure 2.8: Tiny objects comparison . . . . . . . . . . . . . . . . . . . . . .
Figure 2.9: Dense objects comparison . . . . . . . . . . . . . . . . . . . . .
Figure 2.10: Intra-class heterogeneity . . . . . . . . . . . . . . . . . . . . . .
Figure 2.11: Inter-class homogeneity comparison . . . . . . . . . . . . . . . .
. . . . . . . . . . .
Figure 2.12: Qualitative comparison on various datasets

Figure 3.1: Open-Fusion pipeline with two modules for 3D scene reconstruc-

tion and language-based querying . . . . . . . . . . . . . . . . .
Figure 3.2: Qualitative Comparison of 3D object query results on the Replica
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
Figure 3.3: Real-world demonstration of Open-Fusion on a robot platform .

dataset

Figure 4.1: Comparison of representation methods for the task “put the
bowl on the stove,” including raw, PCA, object-centric, and
relation-centric slots . . . . . . . . . . . . . . . . . . . . . . . .

Figure 4.2: An overview of SlotVLA including: Slot-based Visual Tokenizer,
Task-Centric Multimodal Decoder, and LLM Action Decoder.
SlotVLA is flexible in terms of different view settings.

. . . . .

Figure 4.3: Performance comparison of TP, OS, and RS across single-view

. . . . . .
and multi-view manipulation tasks in LIBERO-Goal
Figure 4.4: Simulated trajectory for “put the bowl on the stove” with SlotVLA
visualizations from exocentric and egocentric views . . . . . . .

Figure 4.5: Trajectory demonstration in real life. Task query: “put the car-

7
14
15
18
21

36
38
39
40
41
42
44

50

61
62

65

72

76

79

rot on the plate”. The two most relevant relations are visualized. 80

vii

LIST OF TABLES

Table 2.1: Performance comparison on iSAID valset
. . . . . . . . . . . . .
Table 2.2: Performance comparison on Potsdam valset with clutter . . . . .
Table 2.3: Performance comparison on Potsdam valset without clutter . . .
Table 2.4: Performance comparison on LoveDA testset . . . . . . . . . . . .
Table 2.5: Ablation study of CNN Stem and MDC Block on iSAID, evalu-

ating Params, mIoU, and OA.

. . . . . . . . . . . . . . . . . . .
Table 2.6: Model complexity and performance comparison on Potsdam with-
out clutter, including Params, GFLOPs, runtime, and mIoU . .

28
30
32
34

36

37

Table 3.1: High-level comparison between our Open-Fusion and existing

SOTA queryable scene representations . . . . . . . . . . . . . . .

49

Table 3.2: Comparison of open-set segmentation and 3D scene runtime on

ScanNet dataset . . . . . . . . . . . . . . . . . . . . . . . . . . .

60

Table 4.1: Comparison of methods in terms of design factors. . . . . . . . .
Table 4.2: Manipulation accuracy on LIBERO-Goal by TP, OS, RS (ours) .
Table 4.3: Results of RS under different numbers of slots in single-view

. . . . . . . . . . . . . . . . . . . . . . . . . . . .
Table 4.4: Efficiency of TP and RS with different token settings (i.e. 4, 16)

LIBERO-Goal

67
70

81
81

viii

1

Introduction

Multimodal learning refers to the process of jointly modeling information

from multiple data sources, such as images, language, and depth, with each offering

commonality or complementary perspectives on the same underlying phenomenon.

This approach is inspired by the way humans seamlessly integrate visual, linguis-

tic, and auditory cues to perceive and interact with the world. In recent years,

multimodal learning has received significant attention across AI research due to

its potential to enhance generalization and contextual understanding.

The rapid expansion of multimodal data, supported by the widespread use

of smart sensors, online content, and human-centered technologies, has made this

field both a promising research direction and an increasingly important element

in real-world systems. Typical modalities include vision, language, and audio. In

remote sensing, additional sources such as panchromatic imagery, multispectral

and hyperspectral data, LiDAR, SAR, infrared, and satellite-visible spectrum con-

tribute further diversity. These modalities differ not only in the data format, but

also in their statistical characteristics, and combining them allows for richer, more

robust, and context-aware representations.

Earlier approaches to multimodal fusion often relied on hand-crafted fea-

tures and domain-specific heuristics, coupled with basic fusion strategies. However,

these methods frequently struggle to capture the intricate relationships among

heterogeneous inputs, especially when the modalities vary significantly in struc-

ture, resolution, or noise characteristics. With advances in deep learning (DL),

data-driven models have emerged that automatically learn both intra-modal and

inter-modal representations. These models provide the flexibility to capture com-

plex cross-modal dependencies and have demonstrated strong performance across

diverse benchmark tasks. Depending on the nature of the input modalities and

the goals of the application, many of these methods can be formulated within a

1

unified framework for representation learning and information fusion.

1.1 Architectural Advances in Visual Feature Extraction

Two major neural architectures have been widely adopted for feature ex-

traction in visual tasks: Convolutional Neural Networks (CNNs) and Transformers.

Traditionally, CNNs have served as the foundational building blocks for image-

based recognition systems. Their ability to extract local features through spatially

shared kernels, combined with a hierarchical structure, makes them particularly

effective at modeling spatial patterns. As a result, CNN-based models such as

ResNet [1], U-Net[2], and DeepLabv3[3] have achieved strong performance in tasks

like image classification, object detection, and semantic segmentation.

More recently, the introduction of Transformer architectures has expanded

the design space of DL models. Originally developed for natural language pro-

cessing, Transformers employ self-attention mechanisms to capture long-range de-

pendencies within sequences. Unlike CNNs, they do not assume spatial local-

ity or translation invariance, and instead process input data as sequences of to-

kens. Notably, Vision Transformers (ViT)[4] and their extensions demonstrate

how Transformer-based models can surpass CNNs in a variety of visual recogni-

tion benchmarks.

Transformers have also gained popularity in multimodal learning, not only

because of their strong feature extraction capabilities, but also due to their modality-

agnostic architecture. The same model can be used to process diverse input types

by embedding them into a shared token space. This architectural simplicity and

flexibility make Transformers particularly well-suited for modeling cross-modal re-

lationships, and they now serve as the foundation for many recent advances in

multimodal AI. Recent models such as CLIP[5], Flamingo[6], and BLIP[7] exem-

plify this trend, demonstrating the scalability of Transformers in aligning visual

and textual modalities for tasks like zero-shot classification.

2

1.2 Contributions of the Thesis

Despite the recent progress in multimodal learning, several critical limita-

tions remain that hinder the development of models across real-world visual and

embodied tasks:

(a) Lack of Structural Biases in Visual Representation Models:

While multimodal systems rely on integrating diverse data sources, their perfor-

mance fundamentally depends on the quality of unimodal representations. In vi-

sual tasks such as semantic segmentation of aerial imagery, conventional CNN- or

transformer-based architectures often do not provide sufficient structural inductive

biases that allow them to simultaneously capture fine-grained object boundaries

and global contextual relationships. This results in suboptimal representations

that propagate errors into downstream fusion and reasoning tasks.

(b) Inefficient 3D Semantic Mapping for Multimodal Robotics:

While vision-language (VL) models offer strong semantic understanding, their de-

ployment in real-world scenarios requires representations that associate linguistic

concepts with 3D spatial structure in a compact and retrievable form. However,

existing methods typically store dense per-point features or rely on offline anno-

tations, which are computationally expensive and lack scalability. This limits the

practical use of multimodal reasoning grounded in physical space.

(c) Token Inefficiency and Lack of Relational Structure in VLA

Models: Multimodal systems that integrate visual observations, language instruc-

tions, and action outputs such as vision-language-action (VLA) models, require

structured representations that capture both semantic and relational information.

However, existing VLA models often rely on object-centric inputs that encode

entities independently, without modeling their functional or spatial relationships.

This results in redundant visual tokens and insufficient grounding of language in

task-relevant interactions. The lack of relation-centric modeling, such as between a

robotic gripper and its target, undermines generalization and model transparency

across diverse manipulation tasks.

3

To address these limitations, this thesis presents three frameworks that col-

lectively advance the structured and interpretable modeling of multimodal repre-

sentations by targeting distinct subproblems. Each method is designed to strengthen

a different aspect of the multimodal pipeline: (a) the inductive biases in unimodal

visual encoders and decoders, (b) the integration of semantic and spatial informa-

tion in 3D scene understanding, and (c) the relational grounding of language in

action-driven environments.

In Chapter 2, we introduce AerialFormer, a segmentation framework de-

signed to enhance the structural inductive biases in visual representation models

for aerial imagery. Recognizing the limitations of conventional CNNs and Trans-

formers in capturing both fine-grained details and global context, AerialFormer

combines the strengths of both architectures to improve semantic segmentation

performance in remote sensing tasks. The model is composed of three core mod-

ules: a CNN Stem for preserving high-resolution local features, a Transformer

Encoder for capturing hierarchical and global representations, and a Multi-Dilated

CNN (MDC) Decoder that integrates semantic cues from both the CNN and Trans-

former pathways. By merging local and global information at multiple stages, Aeri-

alFormer effectively addresses the challenge of segmenting small, densely packed,

or ambiguous appearance objects, an area where traditional models often fail. The

model achieves state-of-the-art performance across several remote sensing bench-

marks, demonstrating that carefully structured architectural inductive biases can

improve the quality of unimodal visual representations used in broader multimodal

systems.

In Chapter 3, we introduce Open-Fusion, a real-time 3D mapping frame-

work that bridges semantic reasoning with spatial perception for multimodal robotic

systems. Addressing the challenge of integrating open-vocabulary language embed-

ding with 3D scene representations, Open-Fusion reconstructs a semantic TSDF

volume by incrementally fusing region-level features extracted from RGB-D frames.

These semantic features, derived from a VL model, are stored in an embedding

dictionary and aligned over time using a feature matching algorithm. This de-

4

sign enables efficient storage and retrieval of semantic regions and supports flex-

ible querying using natural language. Open-Fusion thus provides a scalable and

language-grounded 3D representation, making it practical for real-time interaction

and reasoning in unstructured environments.

In Chapter 4, we introduce SlotVLA, a compact and interpretable visual

representation framework tailored for VLA models in robotic manipulation. While

previous approaches often rely on dense visual tokens that indiscriminately en-

code all scene elements, SlotVLA aims to improve efficiency and task grounding

by structuring the visual input around functional object relationships. The core

idea is to represent the visual scene as a small set of slot-based tokens, each cap-

turing interaction-relevant features rather than generic object attributes. SlotVLA

consists of a visual tokenizer that extracts relation-aware slots from ego- and exo-

centric observations and a task-conditioned selection module that dynamically fil-

ters the most relevant tokens based on language input. These tokens are then

passed to a language-conditioned action decoder for manipulation prediction. By

focusing on the interactions between objects and the agent (e.g., gripper-object dy-

namics), SlotVLA reduces token redundancy and enhances relational understand-

ing, which are both critical for generalization across diverse tasks. Experimental

results demonstrate that SlotVLA achieves superior performance on manipulation

benchmarks while using significantly fewer visual tokens than baseline models,

highlighting its efficiency and interpretability advantages.

At the end of this thesis, in Chapter 5, we summarize the proposed solutions

to three core challenges in multimodal learning and conclude with a discussion of

future research directions.

5

2 Multi-Resolution Transformer for Aerial Image Segmentation

2.1 INTRODUCTION

The use of aerial images provides a view of the Earth from above, which

consists of various geospatial objects such as cars, buildings, airplanes, ships, etc.,

and allows us to regularly monitor certain large areas of the planet. Recent ad-

vances in sensor technology have promoted the potential use of remote sensing

images in broader applications, attributed to the ability to capture high-spatial

resolution (HSR) images with abundant spatial details and rich potential semantic

content. Aerial image segmentation (AIS) is a particular semantic segmentation

task that aims to assign a semantic category to each image pixel. Thus, AIS plays

an important role in the understanding and analysis of remote sensing data, offer-

ing both semantic and localization cues for targets of interest. Understanding and

analyzing these objects from the top-down perspective offered by remote sensing

imagery is crucial for urban monitoring and planning. This understanding finds

utility in numerous practical urban-related applications, such as disaster moni-

toring [8], agricultural planning [9], street view extraction [10, 11], land change

[12, 13, 14], land cover [15], climate change [16], deforestation [17], etc. However,

due to the large size of aerial images and limited sensor bandwidth, several chal-

lenging characteristics need to be investigated. Figure 2.1 delineates five principal

challenges, as follows: (i) background–foreground imbalance [18], characterized by

a disproportionate ratio of foreground to background elements (2.86%/97.14%);

(ii) the presence of tiny objects [19], defined as those with dimensions less than 32

× 32 pixels according to the absolute size definition introduced by [20]; (iii) high

object density [19], where objects are closely aggregated; (iv) intra-class hetero-

geneity [21], denoting the variability within a single category in terms of shape,

texture, color, scale, and structure, exemplified by tennis courts displaying diverse

6

appearances; and (v) inter-class homogeneity [21], indicating the visual similarities

shared among objects of distinct categories, such as the comparable appearances

of tennis and basketball courts.

Figure 2.1: Examples of challenging characteristics in remote sensing image seg-
mentation. (Left) (i) The distribution of the foreground and background is highly
imbalanced (black). (Top right) Objects in some classes are (ii) tiny (yellow)
(Bottom right)
and (iii) dense (orange) so that they are hardly identifiable.
Within a class, there is a large diversity in appearance: (iv) intra-class heterogene-
ity (purple); some different classes share the similar appearance: (v) inter-class
homogeneity (pink). The image is from the iSAID dataset, best viewed in color.

Recently, many studies [22, 23] have adopted the use of neural networks,

including Convolutional Neural Networks (CNNs) and Transformers, for AIS due

to the great success shown in the natural image domain. However, for proposed

use cases such as self-driving vehicles [24] and medical imaging [25], many ex-

isting image segmentation methods in computer vision are unable to effectively

address the five characteristics of AIS within a reasonable computational budget.

Typical image backbone models [26, 4], for example, involve a 1/4 downsampling

process that does not prioritize tiny, densely packed objects, frequently resulting

7

(iii)denseobjects(ii)tinyobjects,e.g.,5x15pixelsChallengingcharacteristicsinremotesensing(i)imbalancedforeground-backgrounddistribution(v)inter-classhomogeneity(iv)intra-classheterogeneitybackground(97.14%)TennisCourtwithdifferentappearanceTennisCourtandBasketballCourtsharingsimilarappearanceForeground-backgrounddistributionofiSAIDdatasetin their oversight. Therefore, when designing a segmentation model for remote

sensing imagery, it is crucial to focus on addressing the unique challenges specific

to this domain. CNNs are based on using convolution to compute the local cor-

relation among neighboring pixels. Consequently, CNNs are good at extracting

high-frequency components and localized structures. However, this property leads

to locality and strong inductive biases. Transformers, on the other hand, treat im-

ages as a sequence of embedded patches and model the global correlation among

patches with self-attention mechanisms. Consequently, Transformers are good at

capturing low-frequency components and the global structure. Generally, CNNs

and Transformers exhibit opposite behaviors, where CNNs act like high-pass fil-

ters and Transformers act like low-pass filters. This analysis shows that CNNs and

Transformers are naturally complementary to each other. Thus, combining CNNs

and Transformers can overcome the weaknesses of the two models and strengthen

their advantages simultaneously. To alleviate tiny- and dense-object difficulties, it

is beneficial to utilize detailed local features captured by CNNs. For background–

foreground imbalance, intra-class heterogeneity, and inter-class homogeneity, it is

important to utilize strong semantic representations at both the local level (e.g.,

boundary) from CNNs and the global context level (e.g., the relationship between

objects/classes) from Transformers.

To address the five challenges, including (i) background–foreground imbal-

ance, (ii) the presence of tiny, (iii) densely packed objects, (iv) intra-class hetero-

geneity, and (v) inter-class homogeneity, this paper proposes AerialFormer. The

proposed approach effectively combines the robust feature extraction capabilities

of CNNs with the advanced contextual understanding offered by Transformers,

while maintaining an acceptable parameter increase. The proposed AerialFormer

integrates three key components to address the five challenges. The CNNs Stem is

crucial for high-resolution feature extraction, targeting the precise identification of

tiny and densely packed objects. By maintaining half the size of the input image,

this module serves larger, more detailed features to the decoder. The Transformer

Encoder, leveraging Swin Transformer technology, focuses on capturing complex

8

global relationships. Lastly, the multi-dilated CNN Decoder combines local and

global context to improve detail recognition and accuracy on various scales. This

module ensures computational efficiency, which is comparable to that of plain con-

volution while benefiting from diverse feature representations. The combination of

the Transformer Encoder and multi-dilated CNN (MDC) Decoder effectively ad-

dresses issues such as background–foreground balance and intra-class heterogeneity

and inter-class homogeneity. Our contributions are summarized as follows:

• The proposed approach incorporates a high-resolution CNN Stem that pre-

serves half the input image size, providing larger and more detailed features

to the decoder. This improvement enhances the segmentation of tiny and

densely packed objects.

• This paper introduces a unique multi-dilated CNN Decoder that efficiently

integrates both the local and global context. This module utilizes chopped

channel-wise feature maps with three distinct filters, maintaining computa-

tional efficiency while enhancing the diversity of feature representations.

• The proposed method demonstrates the effectiveness of combining a Trans-

former Encoder with a multi-dilated CNN Decoder and CNN Stem. This

integration successfully addresses challenges such as background–foreground

imbalance, intra-class heterogeneity, inter-class homogeneity, and the seg-

mentation of tiny and dense objects in aerial image segmentation tasks.

2.2 RELATED WORKS

Generally, image segmentation is categorized into three tasks: instance seg-

mentation, semantic segmentation, and panoptic segmentation. Each of these tasks

is distinguished on the basis of its respective semantic considerations. This work

focuses on the second task of semantic segmentation, a form of dense prediction

tasks where each pixel of an image is associated with a class label. Unlike instance

segmentation, it does not distinguish each individual instance of the same object

9

class. The goal of semantic segmentation is to divide an image into several visu-

ally meaningful or interesting areas for visual understanding according to semantic

information. Semantic segmentation plays an important role in a broad range of

applications, e.g., scene understanding, medical image analysis, autonomous driv-

ing, video surveillance, robot perception, satellite image segmentation, agriculture

analysis, etc. This section begins by reviewing DL-based semantic image segmen-

tation and the advancements made in computer vision with Transformers. It then

shifts focus to a review of aerial image segmentation using deep neural networks.

2.2.1 DL-Based Image Segmentation

Convolutional Neural Networks (CNNs) are widely regarded as the de facto

standard for various tasks within the field of computer vision. Long et al. [27]

showed that fully convolutional networks can be used to segment images without

fully connected layers, and they have become one of the principal networks for

semantic segmentation. With the advancements brought by fully convolutional

networks into semantic segmentation, many improvements have been achieved by

designing the network deeper, wider, or more effective. This includes enlarging the

receptive field [28, 29, 30, 31, 32, 33], strengthening context cues [34, 35, 33, 36, 37,

38, 39, 40, 41, 42] leveraging boundary information [43, 44, 45, 25, 46, 47], and in-

corporating neural attention [48, 49, 50, 51, 52, 53, 54, 55, 56]. Recently, a new

paradigm of neural network architecture that does not employ any convolutions

and mainly relies on a self-attention mechanism, called a Transformer, has become

rapidly adopted to CV tasks [57, 58, 59] and achieved promising performance. The

core idea behind the Transformer architecture [60] is the self-attention mechanism

used to capture long-range relationships. In addition, Transformers can be easily

parallelized, facilitating training on larger datasets. Vision Transformer (ViT) [4]

is considered one of the first works that applied the standard Transformer to vision

tasks. Unlike the CNN structure, the ViT processes a 2D image as a 1D sequence

of image patches. Thanks to the powerful sequence-to-sequence modeling ability

10

of the Transformer, the ViT demonstrates superior characterization for extracting

global context, especially in lower-level features compared to its CNN counterparts.

Recent advancements in Transformers over the past few years have demonstrated

their effectiveness as backbone networks for visual tasks, surpassing the perfor-

mances of numerous CNN-based models trained on large datasets. Transformer-

based image segmentation approaches [61, 62, 63, 64, 65, 66] inherit the flexibility

of Transformers in modeling long-range dependencies, yielding remarkable results.

Transformers have been applied with notable success across a variety of computer

vision tasks. These include image recognition [4, 67] object detection [57, 68, 69],

image segmentation [70, 63, 65], action localization [71, 72], and video caption-

ing [73, 74], thereby showcasing their capability to augment global information.

2.2.2 Aerial Image Segmentation

Computer vision techniques have long been employed for the analysis of

satellite images. Historically, satellite images had a lower resolution, and the goal of

segmentation was primarily to identify boundaries such as straight lines and curves

in aerial pictures. However, modern satellite imagery possesses a significantly

higher resolution, and consequently, the demands of segmentation tasks have sub-

stantially increased, which include the segmentation of tiny objects, objects with

substantial scale variation, and entities exhibiting visual ambiguities. To this end,

fully convolutional networks and their variants have become the mainstream solu-

tion for aerial image segmentation and have led to state-of-the-art performances

across numerous datasets [30, 75, 76, 77, 78, 79]. To capture contextual interre-

lations among pixels in remote sensing images, techniques from natural language

processing have also been incorporated into aerial image segmentation [80]. By

imitating the channel attention mechanism [51], S-RA-FCN [81] employs a spatial

relation module to capture global spatial relations, and [82] introduced HMANet

with spatial interaction while balancing between the size of the receptive field and

the computation cost. In HMANet, a region shuffle attention module is proposed

11

to improve the efficiency of the self-attention mechanism by reducing redundant

features and forming region-wise representations.

In recent years, the advance-

ments in transformer-based networks, which leverage self-attention mechanisms to

achieve receptive fields as large as the entire image, have sparked increased inter-

est in their applications. Consequently, there has been a surge in research studies

[83, 23, 84, 64, 22, 85, 86] that have integrated Transformers into remote sensing

applications. In recent state-of-the-art models, hybrid architectures that combine

Transformers and CNNs have demonstrated significant progress. RSSFormer [84]

introduces an Adaptive Transformer Fusion Module that employs Adaptive Multi-

Head Attention (AMHA) and MLP with Dilated Convolution to mitigate back-

ground noise, enhances object saliency, and captures broader contextual informa-

tion during multi-scale feature fusion. DC-Swin [23] introduces a decoder with

a Densely Connected Feature Aggregation Module (DCFAM) to aggregate multi-

scale features from the Swin Transformer encoder. By incorporating dense con-

nections and attention mechanisms, DC-Swin enhances the ability to capture and

utilize multi-scale information and relation-enhanced context. UNetFormer [22] in-

troduces a Global–Local Transformer Block (GLTB), which incorporates efficient

global–local attention using an attention-based branch and a convolutional-based

branch.

This paper introduces AerialFormer, an innovative fusion of a Transformer

encoder enhanced by CNN Stem and a multi-dilated CNN decoder. Although

Transformer-based approaches excel at modeling long-range dependencies, they

face challenges in capturing local details and struggle to handle tiny objects. Thus,

the proposed AerialFormer incorporates a CNN Stem module to effectively support

the Transformer encoders and multi-dilated convolution to capture long-range de-

pendence without increasing the memory footprint at the decoder. The proposed

novel AerialFormer combines the strengths of a Transformer encoder and a multi-

dilated CNN decoder, aided by skip connections, to capture both local context and

long-range dependencies effectively in aerial image segmentation.

12

2.3 METHODOLOGY

2.3.1 Network Overview

An overview of the AerialFormer architecture is presented in Figure 2.2.

The architecture design is fundamentally rooted in the renowned Unet structure

for semantic segmentation [2], characterized by its encoder–decoder network with

the use of skip connections between the matched blocks with identical spatial reso-

lutions on both the encoder and the decoder sides. The composition of the model is

threefold: a CNN Stem, a Transformer Encoder, and a multi-dilated CNN Decoder.

The CNN Stem is designed to be a complement module to the Transformer En-

coder that generates local specific features preserving low-level information at high

resolution, which are subsequently passed to the final concatenation in the decoder,

ensuring that the model retains focus on (ii) tiny and (iii) densely packed objects.

The Transformer Encoder is designed as a sequence of s stages of Transformer

Encoder blocks (s is set as 4 in the architecture) aimed at extracting long-range

context representation. The multi-dilated CNN (MDC) decoder consists of s + 1

MDC blocks with skip connections to obtain information from multiple scales and

wide contexts. The MDC module effectively decodes the rich feature maps of the

Stem module and the Transformer Encoder, addressing the challenges related to

distinguishing similar objects within (i) complex backgrounds and handling (iv)

intra-class heterogeneity and (v) inter-class homogeneity. These components will

be detailed in the following subsections. Given a high-resolution aerial image, it

is first partitioned into a set of overlapping subimages sized H × W × 3, where 3

corresponds to three color channels. Then, each sub-image is fed to AerialFormer,

and the output is the segmentation of H × W .

13

Figure 2.2: Overall network architecture of the proposed AerialFormer, which
consists of three components, i.e., CNN Stem, Transformer Encoder, and multi-
dilated CNN decoder.

2.3.2 CNN Stem

This work proposes a simple yet effective way to inject the local and de-

tailed features of the input image into our decoder through the CNN Stem module.

The proposed CNN Stem serves two crucial purposes in the architecture. Firstly,

it generates larger spatial feature maps to preserve the fine-grained details of tiny

objects, which are often lost during the downsampling process inherent in encoders.

14

Input: Aerial Image (iSAID)TRANSFORMER ENCODERMULTI-DILATED CNN DecoderPatch EmbeddingTransformer Block 1Transformer Block 2Transformer Block 3CNN StemPatch MergingPatch MergingTransformer Block 4Patch MergingMDC Block  MDC Block  MDC Block  MDC Block  MDC Block  Deconv BlockDeconv BlockDeconv BlockDeconv BlockResizeOutput: SegmentationBackgroundShipSTBDTCBCGTFBridgeLVSVHCSPRASBFPlaneHarborSecondly, the Stem module complements the transformer-based encoder by cap-

turing local features, leveraging the inherent strengths of convolutions. These

functionalities of the CNN Stem empower the model to effectively handle (ii) tiny

objects and (iii) high object density. This module is expected to model the local

spatial contexts of images parallel with the patch embedding layer. As shown in

Figure 2.3, our CNN Stem consists of four convolution layers, each followed by

BatchNorm [87], and GELU [88] activation layers. The first 3 × 3 convolutional

layer with a stride of 2 × 2 reduces the input spacial size to half, and through the

following three layers of 3 × 3 convolution with a stride of 1 × 1, the local features

for tiny and dense objects are obtained.

Figure 2.3: Illustrations of the CNN Stem. The Stem takes the input image and
produces feature maps with half of the original spacial resolution.

2.3.3 Transformer Encoder

The Transformer Encoder starts by processing an input image size of H ×

p × W

W × 3, which is tokenized by the Patch Embedding layer, which results in a feature
map H

p × C. The feature map is then passed through a sequence of s = 4
Transformer Encoder Blocks and produces multi-level outputs of different sizes at
each block: H

32 × 8C. Each
Transformer Encoder Block is followed by a Patch Merging layer, which reduces

16 × 4C, and H

8 × 2C, H

4 × C, H

32 × W

16 × W

4 × W

8 × W

15

CNN Stemnorm & activationnorm & activationnorm & activationnorm & activationthe spatial dimension by half before being passed to the next deeper Transformer

Encoder Block.

Patch Embedding

The Transformer Encoder starts by taking an image H ×W ×3 as input and

dividing it into patches of size p × p in a non-overlapping manner. Each patch is
embedded in a vector in the dimensional space of RC by a linear projection, which

can be simplified as a single convolution operation with a kernel size of p × p and a
stride of p × p. Patch embedding produces feature maps of H

p × C. The patch
size determines the spatial resolution of the input sequence of the transformer,

p × W

and therefore, a smaller patch size is favored for dense prediction tasks including

semantic segmentation. Although ViT [4] is a commonly used vision transformer in

computer vision, which processes the 16 × 16 patch and is able to capture a wider

range context, it may not be suitable to capture detailed information. One of the

most challenging aspects of aerial image segmentation is dealing with tiny objects.

On the other hand, the Swin Transformer [89], one of the Transformer variants,

utilizes a smaller patch of 4 × 4. Thus, the Swin Transformer [89] was adopted to

implement a patch embedding layer to better capture the detailed information of

tiny objects in aerial image segmentation.

Transformer Encoder Block

In general, let x ∈ Rh×w×d denote the input of a Transformer Encoder

Block. The Transformer Encoder Block processes the input data with a series of

self-attention and a feed-forward network with residual connection. To compen-

sate the increase in computation because of the smaller patch size, the Swin Trans-

former [89] utilizes a local self-attention instead of global self-attention. Global self-
attention, used in standard Transformers, has a computational cost of O(N 2 · d),

where N is the number of tokens (i.e., N = h × w) and d is the representation

dimension, which can be prohibitively expensive for large images and small patch

16

sizes. The Swin Transformer introduces window-based self-attention (WSA) that

divides the image into non-overlapping windows and performs self-attention within

each window. With WSA, the computational cost is linear to the number of to-
kens, i.e., O(M 2 · N · d), where M 2 is the number of patches within a window, and
M 2 ≪ N . In order to apply the WSA, an input x ∈ Rh×w×d is partitioned into
a group of local patches x′ ∈ R h×w
a batch dimension, i.e., the network parameters are shared along the first dimen-

M 2 ×M 2×d, and the first dimension h×w
M 2

is treated as

sion. Considering the multi-head attention operation with h heads, the feature
dimension d is split into h identical blocks, i.e., R h×w
h ×h. Then, the WSA
can be formulated as

M 2 ×M 2× d

WSA(x′) = [head1; . . . ; headh]WO

(2.1)

where [; ] denotes the channel-wise concatenation of the tensor, WO ∈ Rd×d denotes

the output projection weights, and each head headi is calculated as

headi = softmax

(cid:32)

QiK⊤
i
(cid:112)d/h

(cid:33)

+ B

Vi

(2.2)

iWQ

iWK

i , Ki = x′

i , and Vi = x′

where Qi = x′
value tensors, which are created from the local window with M × M patches with
h feature dimensions by linearly projecting with learnable weights of WQ, WK,
and WV ∈ R d
h . B ∈ RM 2×M 2 is the relative position bias [89] that introduces

h are the query, key, and

iWV

i ∈ RM 2× d

h × d

d

relative positional information into the model.

Because the WSA applies self-attention to the local window, the WSA alone

cannot obtain a global context of the image. To alleviate this issue, the Swin Trans-

former stacks Transformer blocks using WSA and alternates the window location

by half of the window size to gradually build global context by integrating infor-

mation from different windows. Specifically, the Swin Transformer block consists

of a shifted WSA, followed by a 2-layer FFN with a GELU activation function in

17

between, which is formulated as

ˆxl = xl + WSA(norm(xl))

xl+1 = ˆxl + FFN(norm(ˆxl))

(2.3)

where norm indicates the LayerNorm [90] operation, FFN indicates the feed-
forward network, and the partition of the input x is shifted by (⌊ M

2 ⌋) from
the regularly partitioned windows when layer l is even. This process is illustrated

2 , M

in Figure 2.4. For each Transformer Encoder Block, the set of the total number of

layers is denoted as Ls.

Figure 2.4: The figure illustrates a Transformer Encoder Block, showcasing how
it employs localized attention within shifting windows to progressively capture the
global context as the network depth increases.

18

softmaxFFNShift windowpartitionTransformer Encoder Blockfor each window...headswindowPatch Merging

In order to generate a hierarchical representation, the spatial resolution of

each Transformer Encoder Block is reduced by half through the patch merging
layer. The patch merging layer takes as input a feature map size of x ∈ Rh×w×d.

The layer first splits and gathers the feature in a checkerboard pattern, creating

four sub-feature maps x1 to x4 with half of the spatial dimension of the original

feature map, where x1 contains pixels from ’black’ squares in even rows, x2 from

’white’ squares in even rows, x3 from ’black’ squares in odd rows, and x4 from

’white’ squares in odd rows. Then, these four feature maps are concatenated along

the channel dimension, resulting in a tensor of size h/2 × w/2 × 4d. Finally, the

linear projection is applied to reduce the channel dimension from 4d to 2d.

2.3.4 Multi-Dilated CNN Decoder

The proposed decoder with MDC blocks was designed to address challenges

including (i) complex backgrounds, (iv) intra-class heterogeneity, and (v) inter-

class homogeneity, effectively decoding rich feature maps from the Stem module

and the Swin Transformer. Although local fine-grained features are important for

segmenting tiny objects, it is also crucial to consider the global context at the same

time. In the decoder, multiple dilated convolutional operations are used in parallel

with different dilation rates to obtain a wider context for decoding without any

additional parameters. Efficient feature aggregation in the dilated convolutions

selectively emphasizes important spatial information, improving object boundary

delineation, and reducing class confusion. To incorporate these benefits, the multi-

dilated CNN decoder contains a sequence of multi-dilated CNN (MDC) blocks

followed by Deconvolutional (Deconv) blocks, which are detailed as follows.

MDC Block

An MDC Block is defined by three parameters [r1, r2, r3] corresponding to

three receptive fields and consists of three parts: a Pre-Channel Mixer, dilated

19

convolutional layer (DCL), and Post-Channel Mixer.

The MDC Block starts by applying the Pre-Channel Mixer to the input,

which is the concatenation of the previous MDC block’s output and the skip con-

nection from the mirrored encoder, in order to exchange the information in the

channel dimension. The channel mixing operation can be implemented with any

operator that enforces information exchange in the channel dimension. Here, the

Pre-Channel Mixer is implemented as a point-wise convolution layer without any

normalization or activation layer.

The DCL utilizes three convolutional kernels with different dilation rates of

d1, d2, and d3, which allows one to obtain multi-scale receptive fields. The length

of one side of a receptive field r of dilated convolution given a kernel size k and

a dilation rate d is calculated as follows:

ri = di(k − 1) + 1

(2.4)

where the kernel size k is established as 3 for receptive fields that exceed 3 × 3 in

size and as 1 for those receptive fields that are smaller. The dilated convolutional

operation with a receptive field of r ×r is denoted by Convr(·). Then, the proposed

DCL can be formulated as follows:

DCLr1,r2,r3(x) = [Convr1(x1); Convr2(x2); Convr3(x3)]

(2.5)

where x = [x1; x2; x3], i.e.,the tensor after the Pre-Channel Mixer x is sliced into

three sub-tensors with equivalent channel length. As the feature is split to process

with the DCL with three different spatial resolutions, the Post-Channel Mixer is

applied to exchange the information from the three convolutional layers. The Post-

Channel Mixer is implemented with a sequence of point-wise and 3 × 3 convolution

layers, each of which is followed by BatchNorm and ReLU activation layers. This

lets us formulate the multi-dilated convolution (MDC) block as follows. The entire

operation for the MDC Block is illustrated in Figure 2.5.

MDC(x) = PostMixer(DCLr1,r2,r3(PreMixer(x)))

(2.6)

20

where PreMixer refers to the Pre-Channel Mixer and PostMixer refers to the Post-

Channel Mixer.

Figure 2.5: An illustration of the MDC Block, which consists of Pre-Channel
Mixer, DCL, and Post-Channel Mixer.

Deconv Block

The Deconv Block serves to increase the spatial dimensions of the feature

map by a factor of two, while concurrently decreasing the channel dimension by
half. Concretely, this block takes a feature map of size x ∈ Rh/2×w/2×2d and
transforms it into a feature of size x ∈ Rh×w×d. This is achieved utilizing a trans-

posed convolution layer followed by BatchNorm and ReLU activation layers. This

learnable upsampling operation is applied to the output of the MDC block be-

fore concatenating it with the bypassed high-resolution features from the encoder,

providing an opposite functionality to the patch merging block.

21

Pre-Channel Mixernorm & activationnorm & activationPost-Channel MixerMDC Block2.3.5 Loss Function

The network is trained using supervised learning with cross-entropy loss,

which can be formulated as follows:

LCE = −

n
(cid:88)

i=1

ti log(pi)

(2.7)

where ti represents the ground truth, and pi is the softmax probability for the ith
class.

2.4 EXPERIMENTS

2.4.1 Datasets

The proposed AerialFormer is benchmarked on three standard aerial imag-

ing datasets, i.e., iSAID, Potsdam, and LoveDA as below.

• iSAID: The iSAID dataset [91] is a large-scale and densely annotated aerial

segmentation dataset that contains 655,451 instances of 2,806 high-resolution

images for 15 classes,

i.e., ship (Ship), storage tank (ST), baseball dia-

mond (BD), tennis court (TC), basketball court (BC), ground field track

(GTF), bridge (Bridge), large vehicle (LV), small vehicle (SV), helicopter

(HC), swimming pool (SP), roundabout (RA), soccer ball field (SBF), plane

(Plane), and harbor (Harbor). This dataset is challenging due to foreground–

background imbalance, the presence of a large number of objects per image,

limited-appearance details, a variety of tiny objects, large-scale variations,

and high class imbalance. These images were collected from multiple sen-

sors and platforms with multiple resolutions and image sizes ranging from

800 × 800 pixels to 4000 × 13, 000 pixels. Following the experiment setup

[18, 76], the dataset was split into 1,411/458/937 images for train/val/test.

The network was trained on the trainset and benchmarked on the valset.

Each image was overlap-partitioned into a set of sub-images sized 896 × 896

with a step size of 512 by 512.

22

• Potsdam: The Potsdam dataset [92] contains 38 high-resolution images of

6000 × 6000 pixels over Potsdam City, Germany, and the ground sampling

distance is 5 cm. The dataset was divided into 24 images for training and 14

images for validation/testing. There are two modalities included in the Pots-

dam dataset, i.e., true orthophoto (TOP) and digital surface model (DSM).

While DSM consists of the near-infrared (NIR) band, TOP corresponds to

an RGB image. In this work, TOP images were from Potsdam, and DSM

images were ignored. The dataset presents a complex background and chal-

lenging inter- and intra-class variations due to the unique characteristics of

Potsdam. For example, the similarity between low-vegetation and build-

ing classes caused by roof greening illustrates the inter-class difficulty. The

dataset offers two types of annotations with non-eroded (NE) and eroded

(E) options, with and without the boundary. To avoid ambiguity in labeling

boundaries, all experimental results were performed and benchmarked on

the eroded boundary dataset. Following the setup of the experiment [93, 83],

the dataset was divided into 24 images for training and 14 images for test-

ing. The testset of 14 images included 2 13, 2 14, 3 13, 3 14, 4 13, 4 14,

4 15, 5 13, 5 14, 5 15, 6 13, 6 14, 6 15, and 7 13. The dataset consisted

of six categories of surfaces, buildings, low vegetation, trees, cars, and clut-

ter/background. The performance is reported in two scenarios: with and

without clutter. Each image is overlap-partitioned into a set of sub-images

sized 512 × 512 with a step size of 256 by 256.

• LoveDA: The LoveDA dataset [15] consists of 5,987 high-resolution images of

1024 × 1024 pixels and 30 cm in spatial resolution. The data include 18 com-

plex urban and rural scenes and 166,768 annotated objects from three differ-

ent cities (Nanjing, Changzhou, and Wuhan) in China. This dataset presents

challenges due to its diverse geographical sources, leading to complex and var-

ied backgrounds as well as inconsistent appearances within the same class,

such as differences in scale and texture. In alignment with the experimental

23

setup delineated in [15], the dataset was partitioned into 2,522/1,669/1,796

images for training, validation, and testing, respectively. In evaluation sce-

narios involving the testset, the training and validation sets of LoveDA were

amalgamated to create a combined training set, while keeping the testset

unchanged.

2.4.2 Evaluation Metrics

To evaluate the performance, three commonly used metrics were adopted:

mean intersection over union (mIoU), overall accuracy (OA), and mean F1 score

(mF1). These metrics are computed on the basis of four fundamental values,

namely true positive (TP), true negative (TN), false positive (FP), and false neg-

ative (FN). The calculation of these four values involves the utilization of the pre-
diction P ∈ RL×H×W and the class-wise binary ground truth mask GT ∈ RL×H×W ,

where H and W are the height and width of the input image, and L is the number

of classes/categories existing in the input. In the context of multi-class segmenta-

tion, these values are computed for each class l ∈ [1, 2, . . . , L] across all pixels.

TPl =

TNl =

FPl =

FNl =

H
(cid:88)

W
(cid:88)

h=1
H
(cid:88)

w=1

W
(cid:88)

h=1
H
(cid:88)

w=1

W
(cid:88)

h=1
H
(cid:88)

w=1

W
(cid:88)

h=1

w=1

GTl,h,w ∧ Pl,h,w

¬(GTl,h,w ∨ Pl,h,w)

¬GTl,h,w ∧ Pl,h,w

GTl,h,w ∧ ¬Pl,h,w

(2.8)

Based on the four values above, the IoU and F1 of an individual category

l are calculated as follows:

IoUl =

F1l =

T Pl
T Pl + F Nl + F Pl
2T Pl
2T Pl + F Nl + F Pl

(2.9)

(2.10)

24

IoUl and F1l are referred as the IoU and F1 of category l. OA is then

further computed as the ratio of correctly predicted pixels to the total number of

pixels. The mIoU and mF1 are computed as the arithmetic means of the IoU and

F1 score, respectively, for each class category.

OA =

(cid:80)L

l=1 T Pl
l=1(T Pl + F Pl + N Pl + N Fl)

(cid:80)L

mIoU =

mF1 =

1
L

1
L

L
(cid:88)

l=1

L
(cid:88)

l=1

IoUl

F1l

(2.11)

(2.12)

(2.13)

2.4.3

Implementation Details

The proposed AerialFormer-T was trained on a single RTX 8000 GPU,

and the proposed AerialFormer-S and AerialFormer-B on two RTX 8000 GPUs.

The Adam [94] optimizer was employed with a learning rate of 6 × 10−5, weight

decay of 0.01, betas of (0.9, 0.999), and batch size of 8. The experimental models

were trained for 160k iterations for the LoveDA and Potsdam datasets and 800k

iterations for the iSAID dataset. During all training processes, data augmentations

such as random horizontal flipping and photometric distortions were applied.

AerialFormer was trained on three different backbones, i.e., Swin Transformer-

Tiny (Swin-T), Swin Transformer-Small (Swin-B), and Swin Transformer-Base

(Swin-B). The first two backbones were pre-trained on the Imagenet-1k dataset

[95], and the last backbone was pre-trained on the Imagenet-22k dataset [95].

As a result, the experimental performances of the three models AerialFormer-T,

AerialFormer-S, and AerialFormer-B were compared. As introduced in Section

2.3.3, the model hyperparameters including the number of channels C, window
size M 2, and a set of layers L = {Ls}s=4
to each model are delineated as follows:

s=1 in Transformer Encoder Blocks specific

• AerialFormer-T: C = 96, M 2 = 72, L = {2, 2, 6, 2};

25

• AerialFormer-S: C = 96, M 2 = 72, L = {2, 2, 18, 2};

• AerialFormer-B: C = 128, M 2 = 122, L = {2, 2, 18, 2}.

In addition to the aforementioned parameters, the receptive field sizes of the

MDC decoder are noted, which remain constant across the models, detailed as fol-

lows: [r1, r2, r3] = {[1, 3, 3], [3, 3, 3], [3, 5, 7], [3, 5, 7], and [3, 5, 7]}, as demonstrated

in Figure 2.2.

It is worth highlighting that, relative to the commonly utilized CNN back-

bones, the proposed model does not significantly increase computational cost,

as the computational complexities of Swin-T and Swin-S align closely with those

of ResNet-50 and ResNet-101, respectively.

2.4.4 Quantitative Results and Analysis

Quantitative performance comparisons between AerialFormer and other ex-

isting methods are presented in for three different datasets under various settings of

iSAID (valset), Potsdam (with clutter), Potsdam (without clutter), and LoveDA

(testset), respectively. For each dataset, the performance of the proposed Aeri-

alFormer is reported on three backbones of Swin-T, Swin-S, and Swin-B, called

AerialFormer-T, AerialFormer-S, and AerialFormer-B, respectively. The proposed

AerialFormer was benchmarked with CNN-based and Transformer-based image

segmentation methods. The comparison of each dataset is detailed as follows.

iSAID Semantic Segmentation Results

Performance comparisons of the proposed AerialFormer with existing state-

of-the-art methods on the iSAID dataset are presented in Table 2.1. The iSAID

dataset consists of 15 categories and is divided into three groups of vehicles, ar-

tifacts, and fields.

In general, it is observed that AerialFormer-B achieves the

best performance, while both AerialFormer-S and AerialFormer-T obtain compa-

rable results to the second-best methods. All three models significantly outperform

26

other existing methods. Specifically, AerialFormer-T obtains an mIoU of 67.5%,

AerialFormer-S achieves an mIoU of 68.4%, and AerialFormer-B attains an mIoU

of 69.3%. These results present improvements of 0.3%, 1.2%, and 2.1% over the

previous highest score of 67.2% from RingMo [86]. Moreover, on some small and

dense classes (e.g., small vehicles (SVs), planes, helicopters (HCs), etc.), Aeri-

alFormer gains a big margin compared to the existing methods.

In taking the

small-vehicle (SV) class as an example, AerialFormer-T achieves a 1.4% IoU gain,

AerialFormer-S gains a 2.4% IoU margin, AerialFormer-B gains a 2.5% IoU margin

better than that of the best existing method, i.e., RingMo [86]. It should be noted

that RingMo utilizes Swin-B as its backbone, which shares a similar computa-

tional cost with AerialFormer-B. This analysis further shows that AerialFormer-T

and AerialFormer-S, despite being smaller models, outperform the best existing

method, RingMo.

27

Table 2.1: Performance comparison on iSAID valset between AerialFormer and
other state-of-the-art approaches. The performance is reported in mIoU and IoU
for each category. The bold and italic–underline values in each column show the
best and the second best performances. An arrow (↑) indicates that a higher score
is better.

IoU per Category * ↑

Method

Year mIoU ↑

Vehicles

Artifacts

Fields

LV SV Plane HC Ship

ST Bridge RA Harbor BD TC GTF SBF SP BC

UNet [2]

2015

37.4

49.9 35.6 74.7

0.0

49.0

0.0

7.5

46.5

45.6

6.5

78.6

5.5

9.7

38.0 22.9

PSPNet [96]

2017

60.3

58.0 43.0 79.5 10.9 65.2

52.1

32.5

68.6

54.3

75.7 85.6 60.2 71.9 46.8 61.1

DeepLabV3 [3]

2017

59.0

54.8 33.7 75.8 31.3 59.7

50.5

32.9

66.0

45.7

77.0 84.2 59.6 72.1 44.7 57.9

DeepLabV3+ [30] 2018

61.4

61.9 46.7 82.1

0.0

66.2

71.5

37.5

63.1

56.9

73.1 87.2 56.2 73.8 46.6 59.8

HRNet [75]

2019

62.3

61.6 48.5 82.3

6.9

67.5

70.3

38.4

65.7

54.7

75.4 87.1 55.5 75.5 46.4 62.1

FarSeg [18]

2020

63.7

60.6 46.3 82.0 35.8 65.4

61.8

36.7

71.4

53.9

77.7 86.4 56.7 72.5 51.2 62.1

HMANet [82]

2021

62.6

59.7 50.3 83.8 32.6 65.4

70.9

29.0

62.9

51.9

74.7 88.7 54.6 70.2 51.4 60.5

PFNet [76]

2021

66.9

64.6 50.2 85.0 37.9 70.3

74.7

45.2

71.7

59.3

77.8 87.7 59.5 75.4 50.1 62.2

Segformer [64]

2021

65.6

64.7 51.3 85.1 40.3 70.8

73.9

40.8

60.9

56.9

74.6 87.9 58.9 75.0 51.2 59.1

FactSeg [78]

2022

64.8

62.7 49.5 84.1 42.7 68.3

56.8

36.3

69.4

55.7

78.4 88.9 54.6 73.6 51.5 64.9

BSNet [79]

2022

63.4

63.4 46.6 81.8 31.8 65.3

69.1

41.3

70.0

57.3

76.1 86.8 50.3 70.2 48.8 55.9

AANet [77]

2022

66.6

63.2 48.7 84.6 41.8 71.2

65.7

40.2

72.4

57.2

80.5 88.8 60.5 73.5 52.3 65.4

RSP-Swin-T [83]

2022

64.1

62.0 50.6 85.2 37.6 67.0

74.6

44.3

64.9

53.8

73.7 70.7 60.1 76.2 46.8 59.0

Ringmo [86]

2022

67.2

63.9 51.2 85.7 40.1 73.5

73.0

43.2

67.3

58.9

77.0 89.1 63.0 78.5 48.9 62.5

RSSFormer [84]

2023

65.9 — — — — —

—

—

—

—

— — — — — —

W-Net [97]

2023

63.7

55.9 64.8 50.6 18.6 88.9

42.1

61.5

56.7

67.8

59.7 72.1 43.2 80.0 29.5 44.4

FarSeg++ [98]

2023

67.9

65.9 53.6 86.5 42.7 71.7

65.7

41.8

75.8

62.0

76.0 89.7 59.4 75.8 53.6 66.6

MSAug [99]

2024

68.4

67.5 52.6 85.3 41.7 71.7

74.6

46.1

72.2

60.3

79.1 89.8 60.4 77.6 52.3 64.4

PFMFS [100]

2024

67.3

62.8 49.7 84.2 43.1 68.5

68.7

37.1

72.6

56.3

80.0 89.2 56.9 74.1 52.8 65.4

AerialFormer-T –

67.5

67.0 52.6 86.1 42.0 68.6

74.9

45.3

73.0

58.2

77.5 88.8 57.5 75.1 50.5 63.4

AerialFormer-S

–

68.4

66.5 53.6 86.5 40.0 72.1

74.1

44.8

74.0

60.9

78.8 89.2 59.5 77.0 52.1 66.5

AerialFormer-B –

69.3

67.8 53.7 86.5 46.7 75.1

76.3

46.8

66.1

60.8

81.5 89.8 65.0 78.3 52.4 62.4

* Categories in iSAID dataset: large vehicle (LV), small vehicle (SV), plane, helicopter (HC), ship, storage tank (ST),

bridge, roundabout (RA), harbor, baseball diamond (BD), tennis court (TC), ground track field (GTF), soccerball field

(SBF), swimming pool (SP), and basketball court (BC).

28

Potsdam Semantic Segmentation Results

The segmentation performance was analyzed on the Potsdam dataset in

two cases, with and without clutter/background, and the results are summarized in

Table 2.2 and Table 2.3, respectively. The clutter class is the most challenging class,

as it can contain anything except for the five classes of impervious surface, building,

low vegetation, tree, and car. Similar to in other existing work [101, 86, 22], the

proposed AerialFormer was benchmarked using various metrics of mIoU, OA, mF1,

and F1 per category.

• Potsdam with Clutter: Table 2.2 reports the performance comparisons be-

tween our AerialFormer with the existing methods in six classes (that is,

including the clutter class). It should be noted that among all existing meth-

ods, Segformer [64] is a strong transformer-based segmentation model and

obtains the best performance. The proposed model gains a notable improve-

ment of 1.7% in mIoU, 0.9% in OA, and 1.2% in mF1 compared to the best

existing Segformer methods.

Unlike the experiment on iSAID (Section 2.4.4), the trade-off between per-

formance and model size does not seem favorable for this dataset. We speculate

that the cause for this could be the difference in the spatial resolution of the

datasets. According to [102], while the iSAID dataset includes images with spatial

resolutions of up to 0.3 m, the spatial resolution of the Potsdam dataset is finer at

0.05 m. Consequently, objects in the Potsdam dataset are represented with more

pixels, appearing much larger. This might reduce the requirement for architectural

enhancements specifically aimed at improving the segmentation of tiny objects.

As the most challenging category, the F1 score in clutter is the lowest

compared to the other five categories. Due to the challenging clutter category,

many methods have ignored this category and focused on training the network in

only the five other categories, as shown in Table 2.3.

29

Table 2.2: Performance comparison on Potsdam valset with clutter. The perfor-
mance is reported in the mIoU, OA, mF1 and F1 score for each category. Note that
both training and evaluation were performed on the eroded dataset. The values
in bold and italic–underline values in each column show the best and the second
best performance. An arrow (↑) indicates that a higher score is better.

Method

Year mIoU ↑ OA ↑ mF1 ↑

Imp. Surf. Building

Low Veg.

Tree

Car

Clutter

F1 per Category * ↑

FCN [27]

PSPNet [96]

DeeplabV3 [3]

UPerNet [103]

DeepLabV3+ [30]

Denseaspp [31]

DANet [104]

EMANet [105]

CCNet [52]

2015

2017

2017

2018

2018

2018

2019

2019

2019

SCAttNet V2 [101]

2020

PFNet [76]

Segformer [64]

LOGCAN++ [106]

SAANet [107]

MCAT-UNet [108]

AerialFormer-T

AerialFormer-S

AerialFormer-B

2021

2021

2023

2023

2024

—

—

—

64.2

77.1

77.2

76.8

77.1

64.7

65.3

65.6

64.3

68.3

75.4

78.0

78.6

73.8

75.4

—

90.1

90.0

89.7

90.1

—

—

—

—

88.0

—

90.5

-

88.2

83.3

75.9

85.6

85.6

85.6

85.6

76.4

77.1

77.7

75.9

78.4

84.8

86.4

86.6

83.6

84.8

79.5

91.1

87.5

79.3

91.3

87.2

79.7

91.4

87.6

87.6

92.6

92.4

92.5

92.6

87.3

88.5

88.2

88.3

81.8

91.5

92.9

87.5

83.4

84.6

93.5

93.5

93.5

91.6

96.2

95.9

95.5

96.4

91.1

92.7

92.7

92.5

88.8

95.9

96.4

93.8

90.8

92.5

96.9

97.0

97.2

77.8

86.2

86.4

85.5

86.3

76.2

78.8

78.0

78.8

72.5

85.4

86.9

77.2

72.5

74.3

87.2

87.7

88.1

84.6

88.0

87.6

87.5

87.8

83.4

85.7

85.7

85.7

66.3

86.3

88.1

79.8

74.5

76.3

89.0

88.9

89.3

73.5

95.3

94.9

94.9

95.4

77.1

73.7

72.7

73.9

80.3

91.1

95.2

93.1

84.1

83.8

95.9

96.0

95.7

40.3

55.4

56.7

58.0

55.1

43.3

43.2

48.9

36.3

20.2

58.6

58.9

40.1

37.5

41.5

62.5

60.2

61.9

* Categories in Potsdam dataset with clutter: impervious surface (Imp. Surf), building, low vegetation (Low Veg.), tree,

car, and clutter/background.

• Potsdam without Clutter:

In this experimental setting, the review shows

that FT-UNetformer [22], HMANet [82], and DC-Swin [23] obtained the

best scores on the metrics mIoU, OA, and mF1, and none of them could

achieve the best score on all three metrics. On the other hand, the pro-

posed AerialFormer-B scores the best in all three metrics and gains improve-

ments of 1.6% mIoU, 1.7% OA, and 0.9% mF1 compared to FT-UNetformer,

HMANet, and DC-Swin, respectively. Compared to Table 2.2, which con-

30

tains clutter, it can be seen that clutter, when ignored, tends to alleviate

ambiguity between the remaining classes.

Similarly to the observation on the iSAID dataset (Section 2.4.4), it is ob-

served that AerialFormer-B achieves the best performance, while both AerialFormer-

S and AerialFormer-T obtain comparable results as the second-best methods on

the Potsdam dataset in both settings with and without the clutter category.

31

Table 2.3: Performance comparison on Potsdam valset without clutter. The
performance is reported using the mIoU, OA, mF1, and F1 score for each category.
Note that both the training and evaluation were performed on the eroded dataset,
and the clutter category was ignored. The bold and italic–underline values in each
column show the best and the second best performances. An arrow (↑) indicates
that a higher score is better.

Method

Year

mIoU ↑

OA ↑

mF1 ↑

F1 per Category * ↑

Imp. Surf. Building

Low Veg.

Tree

Car

DeepLabV3+ [30]

DANet [104]

LANet [109]

S-RA-FCN [81]

FFPNet [110]

ResT [111]

ABCNet [112]

Segmenter [62]

TransUNet [85]

HMANet [82]

DC-Swin [23]

BSNet [79]

UNetFormer [22]

FT-UNetformer [22]

UperNet

RSP-Swin-T [83]

UperNet-

RingMo [86]

Hi-ResNet [113]

MetaSegNet [114]

ESDINet [115]

AerialFormer-T

AerialFormer-S

AerialFormer-B

2018

2019

2020

2020

2020

2021

2021

2021

2021

2021

2022

2022

2022

2022

2022

2022

2023

2023

2024

—

—

—

81.7

—

—

72.5

86.2

85.2

86.5

80.7

86.1

87.3

87.6

77.5

86.8

87.5

—

—

86.1

87.5

85.3

88.5

88.6

89.0

89.6

89.7

90.8

88.5

91.1

90.6

91.3

88.7

—

92.2

92.0

90.7

91.3

92.0

89.8

89.1

92.0

89.6

92.4

91.9

92.7

89.2

88.1

93.2

93.3

91.5

92.8

93.3

90.8

90.0

91.7

91.3

91.1

92.1

90.5

93.5

93.6

93.8

92.4

93.2

92.0

93.7

93.8

94.0

92.3

91.6

93.1

90.7

93.6

92.7

93.5

91.5

92.4

93.9

94.2

92.4

93.6

93.9

92.7

93.6

93.2

94.6

92.7

95.2

95.3

95.4

95.5

96.4

97.2

94.2

96.7

96.1

96.9

95.3

94.9

97.6

97.6

95.6

97.2

97.2

96.4

97.1

96.5

97.3

96.3

98.0

98.1

98.0

85.7

86.1

87.3

83.8

87.3

87.5

87.9

85.4

82.9

88.7

88.6

86.8

87.7

88.8

86.0

88.0

88.0

85.8

88.1

88.6

89.1

85.0

88.9

89.1

89.6

88.1

88.9

89.8

89.4

83.5

94.2

93.6

96.5

94.8

95.8

88.5

91.3

96.8

96.3

94.6

96.5

96.6

86.0

85.4

89.8

87.1

86.4

92.2

87.9

88.1

87.3

89.1

89.2

89.6

88.6

89.7

88.1

89.1

89.1

89.7

96.1

96.4

95.4

97.3

97.4

97.4

* Categories in Potsdam dataset without clutter: impervious surface (Imp. Surf), building, low vegetation (Low Veg.),

tree, and car.

32

LoveDA Semantic Segmentation Results

The performance comparisons with existing methods are reported based

on the testset splits of the LoveDA dataset in Table 2.4. In this experiment, the

proposed method was evaluated on a public test server (https://codalab.lisn.

upsaclay.fr/competitions/421 (accessed on 18 April 2025)) by sending our pre-

dictions. Our smaller model, AerialFormer-S, achieved a performance comparable

to those of existing state-of-the-art methods, such as UNetFormer [22] and RSS-

Former [84], with a mean mIoU (mean intersection over union) of 52.4%. However,

our best model, AerialFormer-B, shows a significant improvement of 1.7% in mIoU

compared to the existing state-of-the-art methods. Notably, AerialFormer-B out-

performs the existing methods by 4.1% IoU for the road category, 5.2% IoU for the

water category, 2.5% IoU for the forest category, and 5.7% IoU for the agriculture

category. In particular, the ’Road’ category is typically characterized by narrow

and elongated features. Segmenting such objects necessitates both local and global

perspectives, a capability that the proposed model exhibits effectively.

33

Table 2.4: Performance comparison on LoveDA testset between AerialFormer
and other existing state-of-the-art semantic segmentation approaches. The evalu-
ation is based on a submission to the official server. The performance is reported
based on the mIoU and IoU for each category. The bold and italic–underline
values in each column show the best and the second best performances.

Method

Year

mIoU

Background Building

Road

Water

Barren

Forest Agriculture

IoU per Category ↑

FCN [27]

UNet [2]

LinkNet [116]

SegNet [117]

UNet++ [118]

DeeplabV3+ [30]

FarSeg [18]

TransUNet [85]

Segmenter [62]

Segformer [64]

DC-Swin [23]

ViTAE-

B+RVSA [119]

FactSeg [78]

UNetFormer [22]

RSSFormer [84]

2015

2015

2017

2017

2018

2018

2020

2021

2021

2021

2022

46.7

47.8

48.5

47.3

48.2

47.6

48.2

48.9

47.1

49.1

50.6

42.6

43.1

43.6

41.8

42.9

43.0

43.4

43.0

38.0

42.2

41.3

49.5

52.7

52.1

51.8

52.6

50.9

51.8

56.1

50.7

56.4

54.5

48.1

52.8

52.5

51.8

52.8

52.0

53.3

53.7

48.7

50.7

56.2

73.1

73.1

76.9

75.4

74.5

74.4

76.1

78.0

77.4

78.5

78.1

11.8

10.3

12.2

10.9

11.4

10.4

10.8

9.3

13.3

17.2

14.5

43.5

43.1

45.1

42.9

44.4

44.2

43.2

44.9

43.5

45.2

47.2

58.3

59.9

57.3

56.7

58.8

58.5

58.6

56.9

58.2

53.8

62.4

2022

52.4

—

—

—

—

—

—

—

2022

2022

2023

LOGCAN++ [106]

2023

Hi-ResNet [113]

MetaSegNet [114]

ESDINet [115]

GDformer [120]

AerialFormer-T

AerialFormer-S

AerialFormer-B

2023

2023

2024

2024

—

—

—

48.9

52.4

52.4

53.4

52.5

52.2

50.1

52.2

52.0

52.4

54.1

42.6

44.7

52.4

47.4

46.7

44.0

41.6

45.1

45.2

46.6

47.8

53.6

58.8

60.7

58.4

58.3

57.9

53.8

57.6

57.8

57.4

60.7

52.8

54.9

55.2

56.5

55.9

58.1

54.8

56.6

56.5

57.3

59.3

76.9

79.6

76.3

80.1

80.1

79.9

78.7

79.7

79.6

80.5

81.5

16.2

20.1

18.7

18.4

17.0

18.2

19.5

17.9

19.2

15.6

17.9

42.9

46.0

45.4

47.9

46.7

47.7

44.2

45.8

46.1

46.8

47.9

57.5

62.5

58.3

64.8

62.7

59.4

58.0

62.2

59.5

62.8

64.0

Ablation Study

The proposed network’s components were ablated as follows. An ablation

study was performed on the CNN Stem and multi-dilated CNN (MDC) decoder

34

on the tiny (T) model, as shown in Table 2.5. The performance was reported using

the number of parameters, mIoU, OA without background, and OA. To account

for the significant influence of the background class on OA, the OA excluding

the background class is provided. A baseline model featuring a Swin Transformer

encoder and a UNet decoder was evaluated, where the MDC block was replaced

with standard CNN blocks, retaining all original parameters except for the dilation

parameters. Note that MDC does not add any additional parameters compared

to the plain CNN. The baseline performance is the lowest among the configura-

tions, suggesting that both the Stem and the MDC decoder contribute positively

to the overall effectiveness of the model. Specifically, adding the CNN Stem im-

proves +0.2 and +0.3 points in mIoU, and using MDC improves +0.5 and +0.6

points in mIoU. The improvement by examining the overall accuracy (OA) without

the background class was further verified. Specifically, adding the CNN Stem en-

hances accuracy by +0.81 and +0.29 percentage points, while implementing MDC

boosts accuracy by +1.35 and +0.83 percentage points. It is worth noting that the

background class is excluded from this comparison, as it tends to dominate OA

calculations. In Figure 2.6, it qualitatively verifies that the Stem module actually

improves the ability of the model to recognize small and dense objects, but due

to the absence of GT labels on some of the small and dense objects such as small

vehicles in the iSAID dataset, the improvements in quantitative results remain

relatively marginal compared to those of the MDC.

35

Table 2.5: The ablation study results on the CNN Stem and multi-dilated CNN
decoder on iSAID dataset. The table outlines the number of parameters (Params
in millions), mean intersection over Union (mIoU), overall accuracy (OA) without
background, and overall accuracy (OA). Checkmarks (✓) indicate the presence of
the module, and crosses (✗) indicate the absence of the module. Note that the
MDC Block was replaced with a normal CNN Block to evaluate the favorable
properties of the MDC Block.

Method

Stem

MDC

Params (M)

mIoU

OA w/out bg

OA

Baseline

Stem-only

MDC-only

AerialFormer-T

✗

✓

✗

✓

✗

✗

✓

✓

44.92

45.08

42.56

42.71

66.7

66.9

67.2

67.5

74.25

75.06

75.60

75.89

99.03

99.05

99.05

99.06

Figure 2.6: The qualitative ablation study on the CNN Stem and multi-dilated
CNN decoder on iSAID dataset. By comparing Swin-Unet (Baseline) and MDC-
Only with Stem-Only and AerialFormer, it is clear that our Stem module helps to
segment the small and dense objects, highlighted by the red line.

Network Complexity

Besides qualitative analysis, an analysis of the network complexity is in-

cluded, as presented in Table 2.6. This section first details the model parameters

(M), computation (GFLOPs), and inference time (seconds per image) for Aeri-

alFormer. Following that, a comparison of it with baseline models including the

recent Transformer-based architectures [121, 85, 23, 22] is provided. To calculate

the inference time, we averaged the results of 10,000 runs of the model using a

512 × 512 input with a batch size of 1. All the measurements were conducted

on the Potsdam dataset without the clutter class. While AerialFormer-T, with a

model size of 42.7 MB, has a similar model size and inference time to SwinUNet

36

[121], it requires fewer computational resources and achieves a significantly higher

performance (+20.2 in mIoU). The comparison to TransUnet [85] also highlights

the effectiveness of the parameters in the proposed model where we achieve a higher

performance (+18.2 in mIoU) with an inference time of 0.02 seconds per image,

as opposed to 0.023 seconds per image. The comparison to the more recent archi-

tecture using the Swin Transformer, e.g., DC-SwinS [23] and UnetFormer-SwinB

[23], underscores the effectiveness of the proposed architecture. While having less

parameters and a faster inference speed, AerialFormer-T can still outperform those

two models with a noticeable performance gap of +0.9 and +1.0, respectively. The

smallest model in our series, AerialFormer-T, can perform inference at a rate of 50

images per second, while AerialFormer-S, with a model size of 64.0 MB, achieves

35.7 images per second. Even the largest model, AerialFormer-B, with a model size

of 113.82 MB, can achieve a real-time inference speed at 21.3 images per second.

Table 2.6: Comparative analysis of model complexity and performance for dif-
ferent semantic segmentation methods on the Potsdam dataset without clutter,
measured using a 512 × 512 input size. The table outlines the number of pa-
rameters (Params) in millions (M), computational cost in Giga Floating Point
Operations (GFLOPs), inference time in seconds (s), and mean Intersection over
Union (mIoU) scores.

Methods

Params (M)

FLOPs (GB)

Inference Time (s)

mIoU

PSPNet [96]

DeepLabV3+ [28]

Segformer [64]

Unet [2]

SwinUNet [121]

TransUnet [85]

DC-SwinS [23]

UnetFormer-SwinB [22]

AerialFormer-T

AerialFormer-S

12.8

12.5

3.72

31.0

41.4

90.7

66.9

96.0

42.7

64.0

AerialFormer-B

113.8

54.26

54.21

6.38

184.6

237.4

233.7

-

-

49.0

72.2

126.8

0.0097

0.010

0.0089

0.020

0.021

0.023

0.030

0.043

0.020

0.028

0.047

60.3

61.4

65.6

65.5

68.3

70.3

87.6

87.5

88.5

88.6

89.0

37

2.4.5 Qualitative Results and Analysis

This section presents the qualitative results obtained from the proposed

model, comparing them with well-established and robust baseline models, specifi-

cally PSPNet [96] and DeepLabV3+ [30]. This section will illustrate the advantages

of AerialFormer in dealing with the challenging characteristics of remote sensing

images.

• Foreground–background imbalance: As mentioned in Section 2.1, the Intro-

duction, the iSAID dataset exhibits a notable foreground and background

imbalance. This imbalance is particularly evident in Figure 2.7, where cer-

tain images contain only a few labeled objects. Despite this extreme imbal-

ance, AerialFormer shows its ability to accurately segment objects of interest,

as depicted in the figure.

Figure 2.7: Qualitative comparison between AerialFormer and PSPNet [96] and
DeepLabV3+ [30] in terms of foreground–background imbalance. From left to right
are the original image, ground truth, PSPNet, DeepLabV3+, and AerialFormer.
The first row shows the overall performances, and the second row shows zoomed-in
regions. The corresponding regions in the first row are highlighted with a red frame,
and the zoomed-in regions in the second row are connected to their respective
locations in the first row with red lines.

38

Ground Track FieldBackgroundShipStore TankBaseball DiamondTennis CourtBasketball CourtBridgePlaneLarge VehicleSmall VehicleHelicopterSwimming PoolRoundaboutSoccer Ball FieldHarborGround TruthPSPNetOur AerialFormerDeeplabV3+Image• Tiny objects: As evidenced in Figure 2.8, AerialFormer, is capable of accu-

rately identifying and segmenting tiny objects like cars on the road, which

might only be represented by approximately 10×5 pixels. This showcases the

model’s remarkable capability to handle small-object segmentation in high-

resolution aerial images. Additionally, the proposed model demonstrates the

ability to accurately segment cars that are not present in the ground truth

labels (red boxes). However, this poses a problem in evaluating the proposed

model, as its prediction could be penalized as a false positive even if the

prediction is correct based on the given image.

Figure 2.8: Qualitative comparison between AerialFormer and PSPNet [96] and
DeepLabV3+ [30] in terms of tiny objects. From left to right are the original
image, ground truth, PSPNet, DeepLabV3+, and AerialFormer. The first row
shows the overall performances, and the second row shows zoomed-in regions. The
corresponding regions in the first row are highlighted with a red frame, and the
zoomed-in regions in the second row are connected to their respective locations in
the first row with red lines. Some of the objects that are evident in the input are
ignored in the ground truth label.

• Dense objects: Figure 2.9 demonstrates the proficient ability of the proposed

model in accurately segmenting dense objects, particularly clusters of small

vehicles, which often pose challenges for baseline models. Baseline models

often overlook or struggle to identify such objects. The success of the pro-

posed model in segmenting dense objects is attributed to the MDC decoder,

39

Ground Track FieldBackgroundShipStore TankBaseball DiamondTennis CourtBasketball CourtBridgePlaneLarge VehicleSmall VehicleHelicopterSwimming PoolRoundaboutSoccer Ball FieldHarborGround TruthPSPNetOur AerialFormerDeeplabV3+Imagewhich can capture the global context and the CNN Stem that enables the

local details of the tiny objects.

Figure 2.9: Qualitative comparison between AerialFormer and PSPNet [96] and
DeepLabV3+ [30] in terms of dense objects. From left to right are the original
image, ground truth, PSPNet, DeepLabV3+, and AerialFormer. The first row
shows the overall performances, and the second row shows zoomed-in regions. The
corresponding regions in the first row are highlighted with a red frame, and the
zoomed-in regions in the second row are connected to their respective locations in
the first row with red lines.

• Intra-class heterogeneity: Figure 2.10 visually demonstrates the existence of

intra-class heterogeneity in aerial images, where objects of the same category

can appear in diverse shapes, textures, colors, scales, and structures. The red

boxes indicate two regions that are classified as belonging to the category of

‘Agriculture’. However, their visual characteristics differ significantly due to

the presence of greenhouses. Notably, while baseline models encounter chal-

lenges in correctly classifying the region with greenhouses, misclassifying it

as ’Building’, the proposed model successfully identifies and labels the region

as ‘Agriculture’. This showcases the superior performance and effectiveness

of the proposed model in handling the complexities of intra-class variations

in aerial image analysis tasks.

40

Figure 2.10: Qualitative comparison between AerialFormer and PSPNet [96] and
DeepLabV3+ [30] in terms of intra-class heterogeneity: the regions highlighted in
the box are both classified under the ’Agriculture’ category. However, one region
features green lands, while the other depicts greenhouses. From left to right are the
original image, ground truth, PSPNet, DeepLabV3+, and AerialFormer. The first
row shows the overall performances, and the second row shows zoomed-in regions.
The corresponding regions in the first row are highlighted with a red frame, and
the zoomed-in regions in the second row are connected to their respective locations
in the first row with red lines.

• Inter-class heterogeneity: Figure 2.11 illustrates the inter-class homogeneity

in aerial images, where objects of different classes may exhibit similar visual

properties. The regions enclosed within the red boxes represent areas that

exhibit similar visual characteristics, i.e., the rooftop greened with lawn and

the park. However, there is a distinction in the classification of these regions,

with the former being labeled as ’Building’ and the latter falling into the

’Low Vegetation’ category. Although the baseline models are confused by the

appearance and produce mixed predictions, the proposed model can produce

more robust results.

41

BackgroundBuildingRoadWaterBarrenForestAgricultureGround TruthPSPNetOur AerialFormerDeeplabV3+ImageFigure 2.11: Qualitative comparison between AerialFormer and PSPNet [96] and
DeepLabV3+ [30] in terms of inter-class homogeneity: the regions highlighted in
the box share similar visual characteristics but one region is classified as a ’Build-
ing’ while the other is classified as belonging to the ’Low Vegetation’ category.
From left to right are the original image, ground truth, PSPNet, DeepLabV3+,
and AerialFormer. The first row shows the overall performances, and the sec-
ond row shows zoomed-in regions. The corresponding regions in the first row are
highlighted with a red frame, and the zoomed-in regions in the second row are
connected to their respective locations in the first row with red lines.

• Overall performance: Figure 2.12 showcases these qualitative outcomes across

three datasets: (a) iSAID, (b) Potsdam, and (c) LoveDA. Each dataset pos-

sesses unique characteristics and presents a wide spectrum of challenges en-

countered in aerial image segmentation. The major differences among the

methods are highlighted in red boxes. Figure 2.12a visually demonstrates

the efficiency of the proposed model in accurately recognizing dense and

tiny objects. Unlike the baseline models, which often overlook or misclas-

sify these objects into different categories, the proposed model exhibits its

robustness in handling dense and tiny objects, e.g., small vehicle (SV) and

helicopter (HC). As depicted in Figure 2.12b, the proposed model demon-

strates a reduced level of inter-class confusion in comparison to the baseline

42

BuildingLow VegetationTreeCarGround TruthPSPNetOur AerialFormerDeeplabV3+ImageImpervious SurfaceCluttermodels. An example of this is evident in the prediction of building struc-

tures, where the baseline models exhibit confusion. In contrast, the proposed

model delivers predictions closely aligned with the ground truth. Similarly,

in Figure 2.12c, the proposed model’s predictions are less noisy, further as-

serting its robustness in scenarios where scenes belong to different categories

but exhibit similar visual appearances. As in the quantitative analysis, the

performance of the proposed model on the ’Road’ class is visually appealing.

The ability of the proposed model to accurately delineate road structures,

despite their narrow and elongated features, is visibly superior.

43

Figure 2.12: Qualitative comparison on various datasets: (a) iSAID, (b) Pots-
dam, and (c) LoveDA. From left to right: original image, ground truth, PSPNet,
DeeplabV3+, and the proposed AerialFormer. The major differences are high-
lighted in red boxes.

44

(a) iSAID(c) LoveDAGround TrackFieldBackgroundShipStore TankBaseball DiamondTennis CourtBasketball CourtBridgePlaneLarge VehicleSmall VehicleHelicopterSwimming PoolRoundaboutSoccer Ball FieldHarborBackgroundBuildingRoadWaterBarrenForestAgriculture(b) PotsdamImpervious SurfaceBuildingLow VegetationTreeClutterGround TruthPSPNetOur AerialFormerDeeplabV3+CarImageGround TruthPSPNetOur AerialFormerDeeplabV3+ImageGround TruthPSPNetOur AerialFormerDeeplabV3+Image(a) iSAID(c) LoveDAGround TrackFieldBackgroundShipStore TankBaseball DiamondTennis CourtBasketball CourtBridgePlaneLarge VehicleSmall VehicleHelicopterSwimming PoolRoundaboutSoccer Ball FieldHarborBackgroundBuildingRoadWaterBarrenForestAgriculture(b) PotsdamImpervious SurfaceBuildingLow VegetationTreeClutterGround TruthPSPNetOur AerialFormerDeeplabV3+CarImageGround TruthPSPNetOur AerialFormerDeeplabV3+ImageGround TruthPSPNetOur AerialFormerDeeplabV3+Image2.5 DISCUSSION

This section discusses the unique challenges posed by aerial imagery, partic-

ularly in terms of object scale variations and object cutoff, and propose potential

future research directions to address these challenges.

In datasets like iSAID, objects within the same category, such as ships, can

vary significantly in size, with differences in an area of up to 105 times [91]. Cur-

rent fixed-window and patch methods often struggle to accommodate such drastic

changes in scale, potentially leading to misclassification. Moreover, the patch-

based approach used in the encoder can result in object cutoff, where objects are

only partially included in a patch. This can lead to insufficient information for

accurate classification, as evident for objects like buildings class in the Potdam

dataset or field class group in the iSAID dataset. The limited context provided

by the patches can result in incorrect classifications. To address these challenges,

future research should focus on developing methods that can adapt to the varying

scales of objects in aerial imagery. Techniques that dynamically adjust window

sizes or patch dimensions based on object characteristics could be explored. Ad-

ditionally, incorporating contextual information from surrounding patches or em-

ploying attention mechanisms to focus on relevant regions could help mitigate the

issue of object cutoff. Multi-scale feature fusion techniques could also be investi-

gated to capture and integrate information from objects at different scales.

While the proposed AerialFormer demonstrated superior performance in

remote sensing image segmentation, there is still room for improvement in terms

of handling scale variations and object cutoff. Addressing these challenges will be

crucial for developing even more robust and accurate segmentation models in the

future.

45

2.6 CHAPTER CONCLUSION

In this chapter, we propose AerialFormer, a novel approach specifically de-

signed to address the unique and challenging characteristics encountered in remote

sensing image segmentation. These challenges include the presence of tiny objects,

dense objects, foreground–background imbalance, intra-class heterogeneity, and

inter-class homogeneity. To overcome these challenges, this work designed Aerial-

Former by combining the strengths of both Transformer and CNN architectures,

creating a hybrid model that incorporates a Transformer encoder with a multi-

dilated CNN decoder. Furthermore, this work incorporated a CNN Stem module

to facilitate the transmission of low-level, high-resolution features to the decoder.

This comprehensive design allows AerialFormer to effectively capture global con-

text and local features simultaneously, significantly enhancing its ability to handle

the complexities inherent in aerial images.

The proposed AerialFormer was evaluated using three different backbone

sizes: Swin Transformer-Tiny, Swin Transformer-Small, and Swin Transformer-

Base. the proposed model was benchmarked on three standard datasets: iSAID,

Potsdam, and LoveDA. Through extensive experimentation, it was demonstrated

that AerialFormer-T and AerialFormer-S, with smaller model sizes and lower com-

putational costs, achieve performances that are superior or comparable to those of

existing state-of-the-art methods, ranking them as second-best performers. More-

over, the proposed AerialFormer-B surpasses all existing state-of-the-art methods,

showcasing its exceptional performance in the field of remote sensing image seg-

mentation.

46

3 Real-time Open-Vocabulary 3D Mapping and Queryable Scene

Representation

3.1 INTRODUCTION

Real-time 3D scene understanding, crucial in computer vision, involves dis-

cerning object semantics, locations, and geometric attributes from RGB-D data in

unstructured environments [122]. Despite its diverse applications in virtual real-

ity, robotics, and augmented reality, traditional training methods face significant

challenges [123]. These include the need for extensive human annotations, lim-

ited closed-set semantic information, and the demand for real-time performance in

applications like robotics and augmented reality.

In recent years, the convergence of language and robotics has garnered sig-

nificant attention, driven by the promise it holds in enabling robots to interpret

and act upon straightforward natural language commands. This benefit from the

emergence of large-scale vision-language foundation models (VLFMs) such as CLIP

[5], ALIGN [124], BLIP [7], GLIP [125], RegionCLIP [126], etc. Those models are

learned in an unsupervised manner using massive image-text pairs from the internet

and have showcased remarkable capabilities in zero-shot learning and open-vocab

reasoning. However, integrating VLFMs into robotics requires addressing scalabil-

ity and real-time processing concerns. Scalability is essential to avoid exponential

data growth in large environments, while real-time capability is vital for instant

decision-making. Achieving these goals necessitates efficient data extraction and

integration without undue delays.

Despite the impressive qualities exhibited by these VLFMs, there remains a

significant untapped potential for their integration into robotic applications, par-

ticularly in the context of 3D mapping and understanding. The primary bottleneck

in leveraging VLFMs for robotics stems from the fact that most foundation mod-

47

els consume images and produce only a single vector encoding of the entire image

within an embedding space. This approach falls short of meeting the stringent de-

mands of robotic perception systems, which require precise reasoning at point-level

or object-level granularity across a diverse spectrum of concepts. This is crucial for

tasks involving interaction with the external 3D environment, such as navigation

and manipulation. Moreover, it is essential to acknowledge that applying VLFMs

at the point-level can be computationally intensive and time-consuming, rendering

it unsuitable for meeting the real-time demands of real-world applications. There-

fore, to fully harness the potential of VLFMs in robotics, there is a pressing need to

develop more efficient and effective techniques that enable these models to operate

in real-time while delivering the required level of precision for tasks in complex 3D

environments.

In response to the aforementioned challenges, we present Open-Fusion, a

queryable semantic representation rooted in VLFMs. Open-Fusion facilitates real-

time 3D scene reconstruction, incorporating semantics, through the use of the

Truncated Signed Distance Function (TSDF). Our work demonstrates that Open-

Fusion excels in the efficient zero-shot reconstruction and understanding of 3D

scenes, offering queryable scene representations for enhanced understanding and

interaction. To summarize, we make the following contributions: 1) Real-time

3D Scene Reconstruction: We extend TSDF to achieve effective real-time 3D

scene reconstruction. 2) Semantic-aware Region-based Feature Matching:

We extend Hungarian matching to seamlessly match features from the VLFM

into the 3D scene representation, enabling incremental semantic reconstruction.

3) Embedding Dictionary for Efficiency: To reduce memory consumption

during scene reconstruction and facilitate open-vocab scene queries, we implement

an embedding dictionary. 4) Open-Fusion: As a result, we propose Open-Fusion,

a real-time 3D map reconstruction and scene representation with open-vocab query

capabilities. This framework promises to advance the field of real-time 3D scene

understanding for robotics.

48

Table 3.1: High-level comparison between our Open-Fusion and existing SOTA
queryable scene representations. P denotes the number of points in a map, M is
the number of objects in the scene.

Map

Method

Representation

Foundation Model

2D

3D

CoW [127]

NLMap [129]

VLMap [131]

CLIP-Fields [133]

LERF [135]

SemAbs[136]

ConceptFusion [137]

Open-Fusion

point

point

point

NeRF

NeRF

CLIP [5] + GradCAM [128]

ViLD [130] + CLIP [5]

LSeg [132]

Detic [134] + CLIP [5]

CLIP [5]

image patch

occupancy

CLIP [5] + GradCAM [128]

point

TSDF

SAM [138] + CLIP [5]

SEEM [139]

point

bbox

region

Feature

Level

point

bbox

point

bbox

Real-time 1

-

-
✗

✗

✗

✗

✗

✓

Scene-

specific
✗

✗

✗

✓

✓

✗

✗

✗

Sem-
Query 2

O(P )

O(P )

O(P )

-

-

O(P )

O(P )

O(M )

1 Real-time: the real-time requirement for 3D scene reconstruction.
2 Sem-Query: the time for open-vocab semantic query.

3.2 RELATED WORKS

3.2.1 Vision-Language Foundation Models (VLFMs).

VLFMs have brought about a revolution in the field of perception by en-

abling open-set inference using natural language. These models, renowned for

their robust generalization capabilities, owe their success to the extensive datasets

and model parameters that drive them. VLFMs can be broadly categorized into

three groups based on the level of resolution in vision-language alignment as fol-

lows: (i) Image-Level Aligned Models (ILAMs), (ii) Pixel-Level Aligned Models

(PLAMs), and (iii) Region-Level Aligned Models (RLAMs). Specifically, ILAMs

(UniCL [140], CLIP [5], ALIGN [124], BLIP [7], BLIPv2 [141], etc.) generate

a single vector representation for the entire image that can correlate with text

embeddings. PLAMs (LSeg[132], MaskCLIP [142], etc.), on the other hand, pro-

duce vector representation for each pixel of an image. Similarly, RLAMs (GLIP

[125], GLIPv2 [143], RegionCLIP [126], ODISE [144], SEEM [139], HIPIE [145],

SemanticSAM [146], etc.) offer the representation for each region within an image.

Image-level representations offer the advantage of computational efficiency

but are limited by their provision of coarser semantic insights. This limitation

becomes pronounced in contexts demanding finer semantic information, necessi-

tating the integration of auxiliary modules such as Grad-CAM [128] to imbue

49

Figure 3.1: The overall pipeline of Open-Fusion, which contains two modules.
Real-time Semantic TSDF 3D Scene Reconstruction Module: This module takes
in a stream of RGB-D images (It, Dt) and the corresponding camera pose (At).
It incrementally reconstructs the 3D scene, representing it as a semantic TSDF
volume Vt at time t. Open-Vocabulary Query and Scene Understanding Module:
In the second module, Open-Fusion accepts open-vocab queries as inputs and pro-
vides corresponding scene segmentations in response, which can serve as an eye for
language-base robot commanding.

spatial knowledge. However, this integration incurs a substantial increase in com-

putational overhead, rendering such approaches impractical for applications where

real-time processing is desired.

In contrast, pixel-level and region-level Aligned

Models are inherently endowed with spatial awareness, positioning them as more

apt solutions for tasks requiring granular semantic insights. Recognizing the ne-

cessity for both open-set semantics and computational expediency, we have opted

to leverage SEEM, a region-level VLFM with masks. SEEM strikes a balance

between the demand for nuanced semantic understanding and the imperative of

time-efficient processing, all while maintaining scalability.

50

Feature MatchingFeature UpdateFeature ExtractionFeature RenderingOpen-vocab Scene Query"Red Pillow"PoseSemantic TSDF Volume  Rendered Confidence MapFeature Extraction  Temporal Feature MatchingFeature RenderingRegion Confidence MapSemantic Embedding VectorsEmbedding Dict   Real-time Semantic TSDF 3D Scene ReconstructionOpen-Vocabulary Queryand Scene Understandingcurrentviewfrustum Feature UpdateInverse RenderingTSDF IntegrationOpen-Vocab query & surface extractionsemanticswitchRGBDepth3.2.2 Queryable scene representation.

To offer a detailed survey of the current landscape in semantic mapping

methodologies, we examine both two-dimensional (2D) and three-dimensional (3D)

approaches.

2D Mapping: CoW [127] and NLMap [129] are notable examples, harnessing the

open-set features derived from CLIP to construct 2D map for exploration. CoW

employs Grad-CAM [128] to extract spatial knowledge from CLIP whereas NLMap

integrates ViLD [130] to crop objects before applying CLIP. VLMaps [131] stands

out by utilizing pixel-aligned features from LSeg [132] to enable the creation of

bird’s-eye view 2D maps, specifically designed for efficient landmark querying.

NeRF-based 3D Mapping: CLIP-Fields [133] trains a NeRF-inspired implicit rep-

resentation network that maps spatial coordinates (x, y, z) to vectors enriched with

semantic information through MLPs. Remarkably, this approach is scene-specific,

with direct supervision from semantic vectors obtained from CLIP or other models

like Sentence BERT [147]. LERF [135], while also drawing inspiration from CLIP,

focuses primarily on object localization. It trains a neural field through knowledge

distillation from multi-scale CLIP features and DINO. However, it is worth not-

ing that LERF may struggle with capturing precise object boundaries due to its

primary emphasis on object localization.

Non-NeRF 3D Mapping: SemAbs [136] proposed to incorporate semantics from

CLIP with GradCAM and the 3D completion module to produce semantic-aware

occupancy. While it showcases promising results in 3D scene understanding, it

cannot run in real-time. ConceptFusion [137] introduces a unique paradigm by

employing off-the-shelf foundation models to construct 3D maps with open-set

features. While this approach exhibits great potential for open-vocab 3D scene

understanding, their integration of semantics to every points in space makes the

method resource intensive.

While NeRF-based methods excel in achieving photorealistic scene recon-

struction, they require retraining for each new scene and are constrained in the

51

volume they can render. As a result, they tend to be customized for specific

scenes, which limits their applicability to real-world scenarios. Conversely, non-

NeRF-based methods have the potential to capture more generalizable representa-

tions as they might not require retraining for each new scene. However, previous

works focus on the offline generation of the queryable map mainly due to the time-

consuming computational requirements posed by their point-based approach. This

drawback makes them less suitable for real-time robotics applications. To address

this challenge, we introduce Open-Fusion, which is a non-NeRF methods for real-

time processing, resulting in an open-vocab 3D scene representation suitable for

robotics.

3.3 METHODOLOGY

3.3.1 Problem Setup

Consider a sequence of T RGB-D observations obtained from an environ-
t=0. Here, It ∈ RH×W ×3 represents
ment, which can be represented as {(It, Dt, At)}T
an RGB frame, Dt ∈ RH×W indicates a depth frame, and At = [Rt|tt] ∈ R3×4 de-
notes the associated camera pose with rotation R ∈ R3×3 and translation t ∈ R3×1.
Additionally, we have the camera’s intrinsic parameters represented as K ∈ R3×3.

Our primary objective is to construct a language-queryable 3D map denoted as M

in real-time. In this context, we define a queryable map as a 2D/3D representation

of the environment that incorporates both physical and semantic features. These
features can be extracted using a query vector q ∈ Rd. Notably, various entities

such as images, text, coordinates, etc., can be transformed into the query vector

by encoding them into a shared embedding space using an encoding function.

Our proposed Open-Fusion, as depicted in Fig. 3.1, comprises two main

modules: 1) Real-time Semantic TSDF 3D Scene Reconstruction: this module

consists of two sub modules i) Feature Extraction: this module aims to extract

region-based feature including confidence map and embedding map ii) Real-time

Semantic 3D Scene Reconstruction: this module facilitates the integration of an in-

52

coming frame at time t into the current semantic STDF volume Vt−1 while updating

the embedding dictionary (Dt). Consequently, it generates a 3D scene represen-

tation VT and an updated embedding dictionary (DT ) after the integration of T

frames. The second module consists of three components of Feature Rendering by

TSDF, Region-based Semantic Feature Matching, and Feature Update. 2) Open-

Vocab Query and Scene Understanding: this module is designed to localize and

segment objects in the scene based on user queries and open-vocab semantics.

3.3.2 Region-based Feature Extractor

Given the RGB frame of the current view It at time t, we employ the SEEM

model [139], denoted as θ, for encoding. Unlike the widely adopted CLIP model,

SEEM produces region-level aligned features. This aims to eliminate the need for

the class agnostic mask proposal generator in two-stage setup [137] or attention-

explainability model to localize the relevant regions like [127, 136]. Considering the

real-time constraints, avoiding the inclusion of such expensive models in a sequence

of function calls is of utmost importance.

For each It, the model θ generates region confidence maps Ct ∈ R|Q|×H/4×W/4
at a quarter of the input resolution. Additionally, it produces corresponding se-
mantic embedding vectors, denoted as Et ∈ R|Q|×d, tailored for the predefined
number of object queries |Q|, where d is feature dimension. The feature extrac-

tion at time t can be formulated as Ct, Et = θ(It). In practice, the region-based

feature extraction process is specifically for semantic-related tasks and may pose a

bottleneck due to SEEM’s time consumption at 4.5 FPS. If a task doesn’t require

semantics, this process can be skipped. Additionally, given the substantial overlap

between two consecutive frames, it’s feasible to omit some frames. To enhance

the flexibility and efficiency of our OpenFusion, we have implemented a semantic

switch, as depicted in Fig. 1.

53

3.3.3 Real-time 3D Scene Reconstruction with Semantics

Every time-frame, we incorporate the incoming observation (It, Dt, At) into

an implicit surface using the Truncated Signed Distance Function (TSDF). Specif-

ically, we integrate (It, Dt, At) into the TSDF volume Vt−1 to create the TSDF

volume at time t, denoted as Vt.
volume Vt comprises a set of M volumetric blocks, represented as Vt = {Gi}M
i=1.
The TSDF is an extension of the Signed Distance Function (SDF) ϕ, which is a

It is important to emphasize that the TSDF

function that provides the shortest distance to any surface for every 3D point. The

sign indicates whether the point is located in front of or behind the surface. In

the context of scene reconstruction, the points of interest typically reside on the
boundary δΩ. For a distance function d and a point p ∈ R3, the SDF ϕ : R3 → R

defines the signed distance to the surface as follows:

ϕ(p) =

(cid:40)

−d(p, δΩ)

if p ∈ Ω

d(p, δΩ)

if p ∈ Ωc

(3.1)

This means that points located inside the surface have negative values,

while the surface itself lies precisely at the zero crossing point between positive and

negative values. The TSDF truncates all values above with a specified threshold

τ , with τ chosen as four times the voxel size.

As the reconstruction of the 3D scene essentially represents a local 2D

surface—a 2D manifold embedded in 3D space—we can efficiently embed the 3D

scene using globally sparse but locally dense voxel blocks. These voxel blocks

exhibit a distinctive characteristic where they are globally present only near the

surface of interest (while other parts remain void). Within each block, we maintain

a dense voxel grid typically sized at r × r × r. Following the approach in [148],

we construct semantic TSDF volume as a set of globally sparse volumetric blocks
i=1, each containing a locally dense voxel grid Gi = {pj}r3
Vt = {Gi}M
j=1 and the
information in pj = {(RGBj, wj, ˆϕj, kj, cj)} includes color RGB, weight w for
TSDF updates, TSDF value ˆϕ, embedding key k, and confidence score c.

Notably, unlike previous approaches like [137] that store the semantic em-

54

bedding for each point, we opt to store only the keys for embedding and the

associated confidence scores for each pixel. The actual embedding information is

maintained separately within the dedicated embedding dictionary D : k → E.

Given our utilization of region-based embedding for the scene, it’s important to

highlight that the number of embeddings required for the entire scene is signifi-

cantly reduced compared to point-based counterparts. In addition to the surface

and color data, we also incorporate semantics into the TSDF volume. However,

to optimize computation and memory usage in subsequent modules, we limit the

storage of semantics to points near the surface. These points are strategically

sampled based on the TSDF values, resulting in a more efficient representation.

As a result, to integrate (It, Dt, At) at time t into semantic TSDF volume
i=1, we perform the

Vt−1 at time t − 1, consisting of M volumetric blocks {Gi}M
following steps:

1. Feature Rendering: This initial step involves generating a rendered confi-
dence map ˜Ct and retrieving corresponding embedding ˜Et from the existing
TSDF volume Vt−1.

2. Region-based Matching: In this step, we establish the correspondence be-
tween the confidence map Ct and the rendered confidence map ˜Ct for the
update.

3. Feature Update: This step focuses on updating the TSDF volume Vt−1 at

time t and concurrently updating the embedding dictionary Dt based on the

matching.

Feature Rendering by TSDF: We render confidence map ˜Ct with its
corresponding embeding map ˜Et from the TSDF volume with the current camera
pose Rt|tt and depth image Dt at time t. Given the semantic TSDF volume Vt−1

accumulated from time 0 to t − 1 and the current observation (It, Dt, At), our

integration process involves several key steps: (i) Conversion of depth image Dt:
Initially, we convert the depth value Di,j
t obtained from the 2D depth image at the

55

location of pixel coordinates i, j within the image, into a 3D coordinates (x, y, z)

using Eq.3.2.













x

y

z







= R−1

t

Di,j

t K−1



















i

j

1

− tt ,

(3.2)

where Rt and tt are the rotation and translation component of camera pose At,

and K represents intrinsic parameters. (ii) Identifying relevant blocks: Next, we

identify the set of volumetric blocks Gactive that contain points unprojected from

the current depth image. We determine these active blocks within the current

viewing frustum by examining whether the 3D coordinates (x, y, z) fall within the

boundaries of these blocks or not. (iii) Projection of semantic information: Sub-

sequently, we project the voxels Gj within the active blocks that possess semantic

keys and confidence scores onto the image plane, as defined by












u

x









v
ˆd

= ˆK





Rt





y

z





+ tt





,

(3.3)

where ˆK represents the rescaled intrinsic parameters obtained by scaling K to the

θ’s output reslution and the coordinate of the valid voxel (x, y, z) are mapped to the
(cid:17)
(cid:16) ˆd > 0
pixel location (u/ ˆd, v/ ˆd) subjected to

(cid:17)
0 ≤ u/ ˆd < W/4

∧(0 ≤ v/d′ < H/4).

∧

(cid:16)

This projection is a crucial step in incorporating semantic information into

the current frame’s representation. Building upon the rendering operation de-
scribed above, we generate confidence maps ˜Ct ∈ Rm×H/4×W/4 within the current
field of view (FoV).

Region-based Temporal Feature Matching: This step aims to find fu-

sion candidates by matching pairs between the confidence map Ct and the rendered
confidence map ˜Ct, which casts the knowledge of objects accumulated until t − 1
in the semantic TSDF volume from the current FoV. We formulate this feature

matching as a 2D rectangular assignment problem, with the goal of identifying the
assignment S ∗ that maximizes the soft-IoU [149] between Ct and ˜Ct.

56

S ∗ = arg max

n
(cid:88)

m
(cid:88)

S

i=1

j=1

Lmatch⟨Ct, ˜Ct⟩i,jσi,j ,

(3.4)

Here, n represents the number of semantic regions in the current frame, and m

is the number of rendered regions within the current FoV. Lmatch calculates the
soft-IoU of Ct and ˜Ct. The matrix S represents a set of all σi,j values, subject to
the constraints (cid:80)m
i=1 σi,j ≤ 1; ∀j, and σi,j ∈ {0, 1}. If σi,j = 1,
it signifies that the prediction in row i is assigned to the rendered embedding in

j=1 σi,j = 1; ∀i, (cid:80)n

column j. To solve this problem, we employ a modified Jonker-Volgenant algorithm

[150] (extension version of Hungarian). We discard the match if the soft-IoU score

is below 0.10. This operation helps us to avoid fusing poor quality masks of the

same object due to occlusion or blur.

Feature Update and Inverse Rendering: In this step, information,

i.e., (It, Dt, Ct, Et), we obtain from the current time frame is integrated into the

semantic TSDF volume Vt−1 to create Vt. First, each voxel pj within the active

volumetric blocks Gactive undergoes the standard TSDF integration process [148],
where the stored color RGBj and TSDF values ˆϕj are updated using weighted
average. Using Eq. 3.3 with the actual camera intrinsic K, we can obtain (u, v, d)

and the update is summarized as:

RGBj ←

wj · RGBj + Iu/d,v/d
wj + 1

t

ˆϕj ←

wj · ˆϕj + Ψ(Du/d,v/d

t
wj + 1

− d, τ )

wj ← wj + 1

(3.5)

(3.6)

(3.7)

where Ψ(·) is the truncation operation that is applied to SDF to obtain TSDF

(Section 3.3.3).

The dictionary D and the confidence score cj and the associated key kj
will be updated according to the matching S ∗. If the new region is matched to

the existing one, only the confidence map is updated with weighted average while

57

unmatched candidates also update the dictionary as a new region. The confidence

maps Ct are inversely rendered by applying Eq.3.3.

3.3.4 Querying Semantics from the 3D Map

At any time t, we can extract the corresponding point cloud or mesh from

the semantic TSDF volume Vt by querying it with a vector q. Our querying

method involves a similarity calculation between the query and the semantic em-

beddings stored in the dictionary Dt. This approach is significantly faster and

more memory-efficient than previous methods that store embeddings for individ-

ual points. Specifically, we calculate the cosine similarity cos⟨E, q⟩ between the
semantic embeddings E ∈ RR×d in the dictionary Dt and the query vector q ∈ Rd,
which is obtained using a modality-specific encoder trained in a shared embedding

space with the semantic vectors E, and select the most relevant region as the ob-

ject proposal. After the query, Marching Cubes is applied to extract surfaces or

point clouds from the semantic TSDF volumes to indicate the queried region. For

a resource constraint environment, one can simply use the semantic TSDF voxel

coordinates as the approximation of the region.

3.4 EXPERIMENTS

In this section, we conduct a comprehensive evaluation of Open-Fusion’s

performance through both quantitative and qualitative assessments on the Scan-

Net [151] and Replica [152] datasets, specifically focusing on open-set semantic

segmentation tasks. In this work, we will focus our quantitative results and com-

parisons exclusively on the ScanNet dataset and we will provide qualitative results

and comparisons for the Replica dataset.

Furthermore, we showcase the real-

world applicability of Open-Fusion by seamlessly integrating it into the Kobuki

platform, enabling real-time 3D scene representation.

58

3.4.1 Quantitative Benchmarks

Our quantitative experimental benchmarks are conducted on the ScanNet

dataset, a comprehensive RGB-D video dataset with annotations for 3D camera

poses, surface reconstructions, and instance-level semantic segmentations. Follow-

ing the methodology of ConceptFusion [137], we select room-scale indoor scenes

for evaluation of our research. For each selected scene, we utilize the semantic cat-

egories provided in the scene annotations as text-prompted queries for performing

open-set segmentation tasks.

Consistent with the evaluation methodology introduced in ConceptFusion

[137], we assess both performance and time efficiency of Open-Fusion in the context

of open-set semantic 3D scene understanding. Our evaluation encompasses a dual

focus: performance and time efficiency. To assess accuracy, we employ the mean

accuracy (mAcc) and frequency mean Intersection over Union (f-mIoU) metrics. In

addition, we measure time consumption for 3D scene representation in frames per

second (FPS). The measurements were done on single RTX 3090. Table 3.2 offers a

comprehensive comparative analysis between Open-Fusion against existing SOTA

methods in terms of mAcc, f-mIoU, and FPS. Thanks to the utilization of region-

based embedding and TSDF, Open-Fusion achieves nearly real-time performance

at 4.5 FPS, which is 30 times faster than the runner-up ConceptFusion. While

excelling in time efficiency, Open-Fusion maintains competitive performance levels

with the existing SOTA ConceptFusion in terms of both mAcc and f-mIoU metrics.

This experiment underscores the efficiency and effectiveness of Open-Fusion in the

realm of open-set semantic 3D scene understanding. Open-Fusion represents a

significant advancement, establishing itself as the new SOTA in terms of both

performance and efficiency.

59

Table 3.2: Quantitative comparison of open-set semantic segmentation and
3D scene representation time between Open-Fusion and existing methods on
the ScanNet dataset.

Method

LSeg

OpenSeg

CLIPSeg (rd64-uni)

CLIPSeg (rd16-uni)

MaskCLIP

ConceptFusion

Open-Fusion

3
.
v
i
r
P

4
.
S
Z

Time (FPS)↑

Accuracy↑

3D-Rec.1 Sem-3D-Rec2 mAcc f-mIoU

-

-

-

-

-

1.5

50

-

-

-

-

-

0.15

4.5

0.70

0.63

0.41

0.41

0.24

0.63

0.62

0.63

0.62

0.34

0.36

0.28

0.58

0.59

1 3D-Rec.: 3D scene reconstruction only. 2 Sem-3D-Rec: 3D scene reconstruction with semantics.

3 Priv.: finetuned VLFMs specifically for semantic segmentation. 4 ZS: zero-shot approaches.

3.4.2 Qualitative Results

We conducted a qualitative evaluation of Open-Fusion on the Replica dataset

[152], as illustrated in Fig. 3.2. In this experiment, we demonstrated the semantic

segmentation performance with queries involving various object sizes, from small

objects like vases and lamps to larger ones like sofas and cabinets. Our Open-

Fusion not only achieves significantly faster processing times (30x faster) but also

delivers more accurate queryable semantic segmentation results.

3.4.3 Real-World Experiment

In this section, we present a real-world demonstration of real-time queryable

scene reconstruction. Our experiment was conducted using the Kobuki platform,

equipped with an RGB-D camera setup. Specifically, we utilized the Azure Kinect

Camera to capture RGB-D images at a downsampled resolution of 360×630, along

60

Figure 3.2: Qualitative comparison of 3D object query results on Replica dataset.
While ConceptFusion failed to pinpoint the object location, Open-Fusion can es-
timate more precise location from language queries.

61

"TV monitor""Sofa"Ours (4.5 FPS)ConceptFusion (0.15 FPS)Query & Input Scene"Lamp""Cabinet""Vase"Figure 3.3: The Kobuki platform is equipped with an Azure Kinect Camera and
an Intel T265 Camera to demonstrate real-time mapping in a real-world environ-
ment. This system enables interaction with the world through natural language
queries. The system is able to highlight the novel objects like the ”quadruped
robot” or ”chicken taxidermy”.

with the Intel T265 Camera for capturing corresponding camera poses. To ensure

accurate alignment between camera poses and image streams, we synchronized

them based on timestamps and filtered out any images without a matching pose

recorded within a 10 ms timeframe. Fig. 3.3 provides a visual representation of

our real-world experimental setup using the Kobuki platform.

As it is difficult to obtain the ground truth semantic mask for real envi-

ronment, we visually compare the suggested region by the model with the known

environment setup. Fig. 3.3 displays the 3D map reconstruction generated at 50

FPS and semantics updated at 4.5 FPS running on two threads by the Kobuki plat-

form. In this demonstration, we emphasize long-tailed reasoning like ”quadruped

62

Kobuki Platform with AzureKinect and T265 CameraRTX3060M LaptopAzureKinectT265KobukiPlatformReconstructed Scene Over Timerobot” or ”chicken taxidermy”.

3.5 CHAPTER CONCLUSION & DISCUSSION

In this paper, we have introduced Open-Fusion, an efficient approach for

real-time open-vocabulary 3D mapping and queryable scene representation from

RGB-D data. Open-Fusion leverages the VLFM to extract region-based embed-

dings and employs TSDF, along with an extended version of Hungarian matching,

for 3D semantic representation. We conducted both qualitative and quantitative

benchmarks to assess our performance. In a qualitative evaluation, we compared

Open-Fusion with ConceptFusion using the Replica dataset, demonstrating supe-

rior object segmentation results and real-time efficiency. In a quantitative assess-

ment, we compared Open-Fusion with SOTA methods using the ScanNet dataset,

achieving competitive results in terms of mean accuracy (mAcc) and surface mean

Intersection over Union (f-mIoU) while Open-Fusion is 30x faster than Concept-

Fusion. Additionally, we conducted a real-world experiment with the Kobuki plat-

form, highlighting Open-Fusion’s capability in practical applications.

It is worth noting that our dependency on SEEM could limit the audio

queries or multiple language (e.g., Spanish and French) queries presented in Con-

ceptFusion.

63

4

Language-Guided Active Mapping for Robotic Manipulation

This chapter is based on a manuscript currently under review for presenta-

tion at the IEEE/RSJ International Conference on Intelligent Robots and Systems

(IROS 2025).

4.1 INTRODUCTION

Recent advances in vision-language-action (VLA) modeling have signifi-

cantly improved visuomotor control in robotics [153, 154, 155, 156, 157, 158, 159],

integrating language conditions with visual cues to enable precise, multitask ac-

tion prediction across numerous applications [160, 161, 154, 158]. While many

architectures such as OpenVLA [156], Octo [155], ECoT [162], HPTs [163] have

contributed to VLA pipelines, even employing a Large Language Model (LLM) for

action decoding [156, 162], the vision encoder remains a critical bottleneck, as it

serves as the perceptual foundation for action reasoning. In particular, pretrained

encoders such as DINOv2 [164], SIGLIP [165] are widely adopted in VLAs to pro-

duce a large number of visual tokens (e.g., 256 to 512), whose computational costs

can become increasingly prohibitive as the number of visual tokens grows (e.g.

multi-view settings [166]). While these embeddings are rich in information, they

can entangle various information and even redundant background features, limit-

ing interpretability and potentially obscuring task-relevant cues from the action

decoder [167].

Meanwhile, in humans, the performance of manipulation tasks fundamen-

tally depends on understanding the interaction between the actor (e.g., human

actor, robot’s gripper) and relevant object representations [168]. Thus, inspired

by reasoning over sparse modular structures [169, 170] and discrete objects [168],

our research diverges from existing literature to consider a perspective of low-token

representations for multitask robotic manipulation. On the one hand, we aim to

mimic human interactions by proposing an efficient VLA model that relies on a

64

Figure 4.1: Visualization of different representation methods for robotic manip-
ulation: “put the bowl on the stove”. (a) Raw observation, (b) PCA projection of
dense features after token pooling, which provides an entangled embedding at size
four PCA projection of dense features after token pooling (four tokens), which pro-
vides an entangled embedding, (c) object-centric slots, which do not include the
interaction between objects, and (d) Our proposed relation-centric slots, which
model three interaction features between the robot and objects (i.e., robot, robot-
bowl, robot-stove).

minimal set of semantically interpretable visual tokens. While it may be pos-

sible for naive compression to both reduce dense tokens and convey contextual

cues, it inexplicably entangles all kinds of information, obscures relevant objects

and critical relational cues. We analyze an case in Fig. 4.1b, where features from a

strong pretrained ensemble [164, 165] undergo naive token pooling to a size of four.

The resulting PCA projection reveals significant loss of granularity, highlighting

65

(a) Observation(b) Token Pooling’s PCA(c) Object-Centric Slots(d) Relation-Centric Slotsrobotrobot - bowlrobot - stovethe limitations of such compression. On the other hand, we aim to leverage the

fact that common tasks, such as “put the bowl on the stove”, can involve very

few entities (i.e. robot’s gripper, bowl, and stove) [171, 172], and that multi-step

plans can be decomposed into similarly simple tasks [162]. These insights un-

derscore a compelling case for introducing object-centric inductive biases in VLA

models [162, 167, 173, 174, 175].

However, while object-centric cues provide important abstractions and have

been widely used in recent visual understanding [176, 177, 178, 179, 170], they may

be insufficient for robotics. As shown in Fig. 4.1c where objects are captured in-

dependently, there is a lack of gripper-object interaction cues, leaving the action

decoder to infer control parameters from sparse object-centric signals. Robotic

manipulation, however, has required an embodied perspective, explicitly model-

ing both the robot gripper and relevant objects to capture relational patterns (e.g.

tool-object, depth-based interactions [180, 162]). Thus, purely object-based encod-

ings, such as using Slot Attention [181] to encode objects in Fig 4.1c, can struggle

to represent essential actor-object interactions for embodied reasoning.

To address the aforementioned challenges, we propose SlotVLA, a novel

VLA pipeline that emphasizes low-token, relation-centric reasoning for multitask

robotic manipulation. We show in Fig 4.1d, SlotVLA systematically disentangles

not only the object features, but also their relationships with the robotic gripper

as relation-centric slots in a task-relevant manner. Then, it predicts actions us-

ing a minimal set of semantic relation slots, with only four slots employed in our

implementation. Concretely, we first leverage slot attention [181] to parse and tok-

enize semantically meaningful gripper-object interactions from each scene, then we

adopt cross-attention [182] to filter task-relevant slots for action decoding, ensuring

that only a minimal number of visual representations is processed. By focusing

on objects and relational structures, SlotVLA processes the critical spatial and

functional correlations needed for manipulation, even under strict token settings.

In summary, our core contributions are as follows:

66

• We motivate and investigate a novel low-token paradigm for VLA models,

examining the limitations of object-centric cues and naive token compression

for multitask robotic manipulation.

• We present SlotVLA, a relation-centric pipeline that leverages slot attention

to focus on gripper-object interactions, while filtering task-irrelevant infor-

mation. Then, semantic slots can be decoded into action parameters under

severe token constraints.

• We demonstrate that SlotVLA’s structured, compact representations can

perform effectively across different tasks, in both single view, multi-view

settings to offer interpretability and efficiency across manipulation tasks.

As shown in Table 4.1, our work bridges the literature of slot-centric learning

with robotic control. We hope that our work and these contributions can serve as

the groundwork for future research, yielding efficient and interpretable multimodal

approaches that empower multitask manipulation for both simulated and real-

world settings.

Table 4.1: Comparison of methods in terms of design factors.

Method

Object-Centric Relation-Centric Multitask Control

Slot Attention [181]

SlotFormer [183]

OpenVLA [156]

SlotVLA (Ours)

✓

✓

✗

✓

✗

✗

✗

✓

✗

✗

✓

✓

4.2 RELATED WORKS

4.2.1 VLA Learning in Robotic Manipulation.

VLA learning has emerged as a powerful paradigm for instruction-following

agents in various embodied tasks, including 3D scene reconstruction [137, 184,

67

185], navigation [153, 186, 187, 167, 161, 188], cross-embodiment transfer [154, 155],

and, most notably, robotic manipulation [155, 156, 157, 158, 159, 189, 190, 191]. As

visual perception is a critical bottleneck, many recent architectures such as Open-

VLA [156], Octo [155], ECoT [162], HPTs [163] have leveraged strong pretrained

vision encoders, like DINOv2 [164], SIGLIP [165], that are effective at capturing

diverse features. However, they can generate many dense representations that

intermingle object positions, affordances, and backgrounds, making it challeng-

ing for action decoders to isolate task-relevant signals [192], while computational

costs can scale significantly when the number of input views increases [166]. Di-

verging from the recent VLA literature, our research considers a novel low-token

perspective towards performing manipulation tasks. We aim to merit from mim-

icking human reasoning in terms of a few discrete objects [168], and modular

approaches [169, 170] in perceptual understanding. Thus, toward a novel pathway

in efficient and interpretable visuomotor modeling, we design SlotVLA to use as

few as four visual semantic slots for manipulation tasks.

4.2.2 Vision Token Reduction.

Vision-language models process numerous tokens, especially in multi-view

and video reasoning [161, 167]. To reduce costs, compression methods like Token

Merging [193, 194], PruMerge [195], and TokenPacker [196] aggregate tokens, while

Qwen-VL [197] and MQT-LLaVA [198] use Q-former [141] or resamplers [163] for

fixed-length representations. However, these methods prioritize general features

over task-specific and interpretable structures for robotics. Meanwhile, slot-based

learning has recently been leveraged to focus on modular, object-centric structures

in visual reasoning [170, 181, 169, 199, 200], using just a few semantic slots. For

example, SlotFormer [183] used as few as six slots to capture visual dynamics at

object level, and similarly for SlotSSM [169] to perform memorization tasks. Un-

like existing works, our SlotVLA extends the slot attention mechanism to robot

manipulation tasks, particularly by improving upon object-centric slots to form

68

gripper-object interaction semantics, preserving their relational features for multi-

task manipulation control.

4.3 PROBLEM FORMULATION

4.3.1 Low-Token Visual Representations

A central theme of our work is low-token representations, where we con-

strain the number of visual tokens fed into our reasoning module. Traditionally,

visual encoders generate a large number of tokens (e.g., K ∈ [256, 512]) for single-

view and multi-view processing.

In contrast, our baseline low-token approach

compresses or directly reduces these tokens to a small set (e.g., 4 tokens). On top

of mimicking human reasoning, which uses a few object-specific representations for

interactions [168], this work aims to simultaneously (1) improve interpretability of

visual representations, forcing the model to reason on more compact representa-

tions, and (2) maintain computational efficiency as LLM’s costs grow quadratically

with the number of tokens.

Formally,

t } represent a dense set of visual to-
kens/patches from the feature map encoded by a visual encider from the image It

let vt = {v1

t , . . . , vK

t , v2

at time t. Our goal is to learn a function g(.) such that,

st = g(vt) with st = {s1

t , . . . , sN

t },

(4.1)

where st is a compact set of tokens of size N ≪ K. This strategy offers a straight-

forward way to restrict the model’s input size for downstream reasoning tasks.

4.3.2 Limitations of Naive Reduction Strategies

In Table 4.2, we present analytic results on different token reduction strate-

gies for manipulation tasks on LIBERO-Goal, at varying tokenization sizes (i.e., 4

and 16):

• Token Pooling (TP): st encodes blended representations, mixing object and

background features (Fig 4.1b).

69

Table 4.2: Manipulation accuracy on LIBERO-Goal by TP, OS, RS (ours). Best
results are bolded, second-best underlined.

Type

TP 16

TP 4

OS 16

OS 4

Single-View

Multi-View

Prominent Fine

Long

All

Prominent Fine

Long

All

75.8%

70.0%

62.5%

75.8%

45.0% 5.0% 59.5%

31.7% 30.0% 54.5%

18.3% 10.0% 44.0%

36.7% 20.0% 58.5%

82.5%

85.0%

75.8%

85.0%

53.3% 50.0% 70.5%

38.3% 60.0% 68.5%

40.0% 25.0% 60.0%

51.7% 30.0% 69.5%

RS 4 (ours)

80.8%

35.0% 40.0% 63.0%

87.5%

55.0% 60.0% 75.0%

• Object Slots (OS): st encodes independent object representations without

interaction modeling (Fig 4.1c).

• Relation slots (RS) (Ours): st encodes gripper-object interactions for action

reasoning (Fig 4.1d).

For OS and RS at size four, we retain only task-centric slots (see 4.4.2), which

highlight key benefits to capturing interaction dynamics while preserving relevant

object details.

Token Pooling: Entangles Relevant and Irrelevant Features

Directly compressing a dense set of tokens vt into a smaller set st can lead

to entanglement of relevant and irrelevant features, as the model retains both task-

critical and redundant background information. This reduces semantic granularity

and makes it harder to extract meaningful, interpretable cues (see Fig. 4.1b). Be-

cause token aggregation merges features from different parts of the scene, object

boundaries become blurred within individual tokens, making object-level separa-

tion less distinct. We quantitatively show in Table 4.2: TP exhibits a performance

drop as token size decreases (e.g., TP 16 vs. TP 4). While TP maintains reason-

able accuracy for prominent objects, it struggles with fine and long robot manip-

ulation tasks, indicating a lack of explicit feature separation. This suggests that

70

at lower token counts, the inability to distinguish individual objects can impair

spatial reasoning, leading to degraded manipulation accuracy.

Object Slots: Missing Relational Cues

To analyze the case where st encodes independent object representations

as object slots, Table 4.2 shows that OS remains competitive with TP at token

number 16, yet it still comparatively underperforms overall and in fine-grained

reasoning. While object-centric representations provide structured encoding of

individual objects, they may be insufficient for capturing interaction-based infor-

mation, particularly between the gripper and target objects. Since manipulation

actions inherently depend on interactions between the actor and objects [162],

OS’s reliance on independent object representations may lack critical relational

cues, so the action decoder must infer spatial relationships and actions based on

sparse object-centric signals. This limitation is observable in Fig.4.1c, where all

objects in the scene are captured, but gripper-object interactions remain unclear.

On the other hand, scaling the number of slots (i.e. OS 16) may just include more

irrelevant objects and reduce robot manipulation effectiveness.

Meanwhile, RS is designed to capture both interaction information and fine-

grained details, allowing it to effectively handle various tasks using a few relevant

tokens.

4.4 METHODOLOGY

In this section, we propose SlotVLA, a multimodal large language model

(MLLM) framework for robotic manipulation. SlotVLA relies on three main com-

ponents: (i) a slot-based visual tokenizer that can process exocentric or ego-exo

views into relation-centric visual tokens via relation-centric learning, (ii) a task-

centric multimodal decoder to filter for tokens most aligned with the text embed-

ding space, and (iii) a LLM action decoding for processing multimodal represen-

tations into precise control parameters. Fig. 4.2 illustrates the design of SlotVLA.

71

Figure 4.2: An overview of SlotVLA including: Slot-based Visual Tokenizer,
Task-Centric Multimodal Decoder, and LLM Action Decoder. SlotVLA is flexible
in terms of different view settings.

4.4.1 Slot-Based Visual Tokenization

Manipulation requires isolating objects that the robot interacts with, yet

existing perception strategies often process dense image features entangled with

72

LLM Action DecoderSlotVLALoRALLM TokenizerΔx, Δθ, ΔgraspTask-Centric Multimodal DecoderExo-viewEgo-viewVisual Encoderrobot push the plate tothe front of the stoveRelation-centricLearningSlot AttentionFeature MapLearnableSlotsDepth MapBounding BoxFlexible inputviewFrozenWeightTrainableWeightLanguageInstructionTask-centricTokensLanguage TokensRelation-centric LearningSlot-basedVisual TokenizerRelation-centricTokensirrelevant objects and background redundancies. Thus, on top of the visual en-

coder, we leverage slot attention [181] to develop a tokenization function g(·) that
processes semantical dense patches in vt ∈ RK×Denc using a set of learnable queries
t }, st ∈ RN ×Dslot. This design aims to capture the underlying mod-
st = {s1
ular semantics [201, 202] of vt through an iterative process with Gated Recurrent

t , . . . , sN

Unit (GRU) [203],

, where a =

1
√
D

qk⊤.

(cid:80)N

eai,j
l=1 eal,j
˜ai,j

˜ai,j =

wi,j =

(cid:80)HencWenc
l=1

˜ai,l

,

st = GRU(inputs = wv, states = st).

where three linear transformation heads are used to map the learnable slots st and
frame-wise feature maps vt into Query q ∈ RN ×Denc, Key k ∈ RK×Denc, and Value
v ∈ RK×Denc and Denc indicate the encoded channel dimension. The attention
weights ˜a are produced by normalizing with softmax along the slot dimension, and

the weighted mean coefficient w aggregates the Value v to update the slots.

Relation-Centric Learning.

While object-centric tokens localize items of interest, they do not inherently

capture interactions between the gripper and objects. In robotic tasks, understand-

ing where interactions between objects are and how far they are from each other is

crucial to planning grasps and manipulations. Thus, unlike existing slot attention

algorithms that focus on learning an object-centric training objective for object

discovery and tracking [181, 183], we extend the slot attention approach to learn

relation-centric tokens with three key improvements as follows:

1. Interaction Spatial Localization. Given the object i bounding box (xi

t, yi
t , yg
t ) (g is a unique object index
for the gripper across frames) at frame It that occurs interaction, we lever-

and the gripper g bounding box (xg

t , wg

t , hg

t, wi

t, hi
t)

age a prediction head to predict the union-based ri bounding box coordinates

73

(xri
t , yri
min(xi

t , wri
t , hri
t ) that encloses both object i and gripper g. Specifically, xri
t =
t, xg
yri
hri
t = min(yi
t + wi
t ),
t =
t +hg
t, yg
t )−yr
t+hi
t . The loss provides explicit location and scale cues un-
(cid:17)

max(yi
der binary cross-entropy, Lbbox = − (cid:80)
where ypred, ygt respectively denote predicted and groundtruth values. This

t = max(xi

k ) log(1 − ypred

k + (1 − ygt

t ), wri

t ) − xri
t ,

k log ypred
ygt

t + wg

t, xg

t, yg

k∈{x,y,w,h}

(cid:16)

)

k

relation-centric bounding box highlights the spatial extent of gripper-object

interaction, focusing the representation on crucial contact or near-contact

regions.

2. Interaction Depth Awareness. For each bounding box of the joined

region, we also predict its spatial depth using an L1-based loss Ldepth =
∥Dpred − Dgt∥1 that clarifies the box-conditioned placement in 3D space,
based on depth prediction Dpred and ground truth Dgt. This provides an

actionable context for manipulation.

3. Temporal Association. For slot consistency through time, we performed

training by sampling sequences that correspond to each object identity. Then,

we align our slot predictions with each identity using Hungarian matching

on pairs of sequences.

While interaction spatial localization can capture precise object-gripper interac-

tions, depth interaction provides awareness of obstacles and relative distances,

allowing for accurate grasping while avoiding collision. Combining relation region

detection and depth estimation yields a total loss:

Lrelation = αLbox + βLdepth,

(4.2)

where α and β are weighting factors. By directing the model’s attention to critical

regions cross-entity instead of isolated objects alone, these simple and straight-

forward strategies provides semantically rich tokens that significantly improve the

accuracy of the manipulation (Table 4.2).

74

4.4.2 Task-Centric Multimodal Decoder

While leveraging a relation-centric approach is practical for robotic manip-

ulation, not all slots are relevant to a given task. We thus introduce a task-centric

multimodal decoder using cross-attention CrossAttn, followed by a F F N (Feed-

Foward Network) to estimate the relevance scores of the tokens with regards to

the specified manipulation query. Concretely, our decoder, parameterized by Θ,

computes cross-attention and predicts the relevant scores πt at time t between the

relation slots st and the embeddings of language tokens (denoted as TaskEmb):

πt = F F N (CrossAttnΘ(st, TaskEmb)).

(4.3)

where TaskEmb is encoded by the LLM tokenizer as the task context (i.e., a lan-

guage instruction prompt).

Then, using the score, we choose to retain κ most relevant slots during

training and inference with a T opκ function and filter out the rest. Given the
relation slots st, we extract a refined subset ˜st = {˜s1
t } to serve as task-
centric tokens, where κ ≤ N , based on their scores:

t , . . . , ˜sκ

˜st = {si

t | i ∈ T opκ(πt)}.

(4.4)

This selection process ensures that only the most task-relevant slots contribute to

downstream tasks.

4.4.3 LLM Action Decoding

Inspired by [167], we employ LoRA [204] to integrate these tokens into a

finetuning-based VLA framework that leverages an LLM action decoder, which

we denote as ActionDecoder(·). After the task-centric multimodal decoder (Sec-
tion 4.4.2), the reduced set of relation-centric tokens {˜sj

t=1 is concatenated with
language embeddings from the task query to form a multimodal input sequence.

t }κ

Then, we define the action prediction as a classification problem, where each con-

trol dimension (e.g., positional shift ∆x, rotational adjustment ∆θ, and grasp

75

Figure 4.3: Performance comparison between TP, OS and RS across different ma-
nipulation tasks in single-view (top) and multi-view (bottom) settings of LIBERO-
Goal. Tasks are categorized into Prominent, Fine, and Long, as separated by yellow
dashed lines.

state transition ∆grasp) is discretized. Let yt be the ground-truth action token at

time step t and ˆyt = ActionDecoder(˜st || T askEmb) be the predicted probability,

where || denotes concatenation operation, formulated as:

LCE = −

L
(cid:88)

t=1

yt log ˆyt,

(4.5)

where L is the total number of action steps. By focusing on key task-centric slots

that pass through the Task-Centric Multimodal Decoder, the LLM-based policy

can efficiently facilitate multitask robotic manipulation.

76

75.0%90.0%60.0%90.0%60.0%45.0%35.0%45.0%15.0%30.0%54.5%90.0%75.0%65.0%90.0%70.0%65.0%20.0%65.0%25.0%20.0%58.5%100.0%85.0%70.0%95.0%90.0%45.0%35.0%65.0%5.0%40.0%63.0%0.0%20.0%40.0%60.0%80.0%100.0%put the bowl onthe stoveput the bowl ontop of thecabinetpush the plateto the front ofthe stoveturn on thestoveput the winebottle on top ofthe cabinetput the bowl onthe plateopen the middledrawer of thecabinetput the creamcheese in thebowlput the winebottle on therackopen the topdrawer and putthe bowl insideALL90.0%80.0%70.0%100.0%85.0%85.0%40.0%45.0%30.0%60.0%68.5%95.0%90.0%60.0%95.0%95.0%75.0%45.0%50.0%60.0%30.0%69.5%100.0%75.0%80.0%100.0%85.0%85.0%50.0%55.0%60.0%60.0%75.0%0.0%20.0%40.0%60.0%80.0%100.0%put the bowl onthe stoveput the bowl ontop of thecabinetpush the plateto the front ofthe stoveturn on thestoveput the winebottle on top ofthe cabinetput the bowl onthe plateopen the middledrawer of thecabinetput the creamcheese in thebowlput the winebottle on therackopen the topdrawer and putthe bowl insideALLToken PoolingObject  SlotRelation  SlotProminent-Target ManipulationFine-Target ManipulationLong-HorizonSingle-ViewProminent-Target ManipulationFine-Target ManipulationLong-HorizonMulti-View4.5 EXPERIMENTS

4.5.1 Experimental Setup

Evaluation: For each of our comparisons (Fig. 4.3, Tables 4.3, 4.4, we

evaluate SlotVLA as a single model trained for multiple tasks, under different

tokenization strategies. We perform evaluations on 10 simulated tasks of LIBERO-

Goal [171], an example shown in Fig 4.4, which we decompose into different task

types,

• Prominent-Target Manipulation (Prominent): Tasks involve clearly distin-

guishable objects central to execution (e.g., “putting the bowl on the stove.”).

• Fine-Target Manipulation (Fine): Requires precise object placement (e.g.,

“placing cream cheese in a bowl.”).

• Long-Horizon Manipulation (Long): Involves multi-step tasks requiring se-

quential execution (e.g., “opening a drawer and placing a bowl inside.”).

For each task, we perform 20 random trajectories and report the success rate. Our

real evaluation results are shown in the Supplementary, with an illustration shown

in Fig 4.5.

Modeling: We perform analyses with naive TP [205], and OS, RS using

slot attention [181] that respectively capture object-centric, relation-centric fea-

tures under SlotVLA.

Implementation: We use an ensemble of pretrained Visual Encoders DI-

NOv2 [164], SIGLIP [165] that are frozen to produce initial visual embeddings.

For LLM tokenizer and action decoding, we employ LLama-2 [206] pretrained on

Open-X Embodiment [190].

In order to prepare OS and RS, we perform two

training steps: (1) we first pretrain the object-/relation-centric tokenization on

object-/relation-centric labels, then (2) we use LoRA to finetune on the training

data before running the evaluation. For TP we adopt only (2) with SlotVLA.

77

In the realistic task benchmark, we labeled object positions before learning the

relation-centric representations for action control.

4.5.2 Main Results

We present our main results in Fig. 4.3, evaluating both single-view (top)

and multi-view (bottom) setups. In these experiments, we compare our proposed

RS with TP, OS and we report performance on 4 tokens (single-view) and 8 to-

kens (multi-view). The findings show that incorporating the wrist view notably

enhances manipulation outcomes.

In particular, SlotVLA achieves a significant

improvement, rising from 63.0% to 75.0%.

Prominent-Target Manipulation. Both OS and RS outperform TP

on simple tasks such as “putting the bowl on the stove” and in overall accuracy.

Interestingly, OS proves effective in tasks like “putting the bowl/wine bottle on top

of the cabinet”, suggesting that the action encoder can adequately interpret object

relationships when visual clarity is high. However, RS demonstrates a general

advantage, achieving average accuracies of 80.8% in single-view and 87.5% in multi-

view settings, compared to OS’s 75.8% and 85.0%, respectively. This highlights

RS’s superior capacity at interacting with prominent targets.

Fine-Target Manipulation. When met with demands for precise spatial

reasoning, all three methods struggle. RS usually outperforms OS and TP, ex-

celling in “putting the cream cheese in the bowl” at 65.0% accuracy in single-view,

compared to OS’s 45.0% and TP’s 35.0%. Similar trends hold in multi-view. While

RS achieves the highest average accuracy at 55.0% in the multi-view setting, com-

pared to OS’s 51.7% and TP’s 38.3%, it struggles with “putting the wine bottle

on the rack” in single view, possibly due to difficulty in distinguishing the precise

placement on the rack.

Long-Horizon Manipulation. While explicit relational modeling offers

advantages, long-horizon tasks remain challenging for all approaches. TP achieves

only 30.0%/60.0% in single/multi-view settings, whereas SlotVLA’s RS improves

78

Figure 4.4: Trajectory demonstration in simulation from exocentric, egocentric
views. Task query: “Put the bowl on the stove”. RS’s two most relevant slots are
visualized via predicted bounding boxes and depth maps, with colors indicating
slot indices. SlotVLA (1) captures interaction features over time, (2) encodes fine-
grained depth cues (e.g., the bowl’s side in egocentric view).

slightly to 40.0%/60.0%. OS performs the worst, at just 20.0%/30.0%, suggesting

that the action decoder struggles to interpret sparse signals in multi-step tasks.

Demonstrations. Fig. 4.4 qualitatively showcases SlotVLA’s ability to

track relation-centric, task-relevant interactions using RS in both exocentric and

egocentric views for “put the bowl on the stove.” SlotVLA can maintain con-

sistent robot-object slots over time, thus highlighting SlotVLA’s capabilities for

action decoding from RS. Additional real-world benchmarks are provided in the

Supplementary (Fig. 4.5).

4.5.3 Ablations

Scaling of Relation Slots. Table 4.3 shows that RS achieves the highest

accuracy (63.0%) with four slots, effectively balancing fine-grained and interaction-

79

Task: robot put the bowl on the stoverobot-bowlrobot-bowlrobot-stoverobot-stove(exocentric view)(egocentric view)Figure 4.5: Trajectory demonstration in real life. Task query: “put the carrot on
the plate”. The two most relevant relations are visualized.

aware representations. This aligns with the small number of key entities involved

(e.g., gripper, bowl, stove; Fig 4.4). Fewer slots (e.g., three) may fail to consistently

capture interaction dynamics due to potential failures in localization, while more

slots introduce redundancy without clear benefits. These findings highlight RS’s

compact usage for multitask robotic manipulation.

Efficiency Analyses. Table 4.4 compares the efficiency of TP, OS, and

RS across single-view and multi-view settings. Our proposed RS consistently out-

performs TP in accuracy—even surpassing TP 16 while using only four tokens.

Despite comparable GFLOPS in the four-token setting, RS offers a clear accuracy

advantage. Meanwhile, inference speed across all methods remains practical, av-

eraging at 15 fps in single-view and 12.4 fps in multi-view, demonstrating that RS

80

(exocentric view)Task: robot put the carrot on the platerobot-carrotrobot-plateTable 4.3: Results of RS under different numbers of slots in single-view LIBERO-
Goal

Slot Size

3

4

8

16

Prominent

74.2% 80.8% 75.8% 76.7%

Fine

Long

All

30.0% 35.0% 33.3% 33.3%

15.0% 40.0% 35.0% 15.0%

55.0% 63.0% 59.0% 57.5%

Table 4.4: Efficiency of TP and RS with different token settings (i.e. 4, 16). Best
results are bolded, second-best underlined.

Metric

Single-view

Multi-view

TP 4 OS 4 RS 4 TP 16 TP 4 OS 4 RS 4 TP 16

↑ Accuracy (%)

54.5

58.5% 63.0

59.5

68.5

69.5

75.0

70.5

↓ GFLOPS

416.04 417.07

417.07

496.18

627.25 629.30

629.30

787.54

is both efficient and effective for robotic manipulation.

4.6 CHAPTER CONCLUSION

In this paper, we introduced SlotVLA, a framework that constructs relation-

centric representations that are compact, yet semantically rich for multitask robotic

manipulation. By leveraging slot attention, SlotVLA disentangles object entities

from their context while capturing interaction features relevant to manipulation.

Our approach enables further slot filtering through language conditioning, such

that only task-relevant semantic slots are used for action decoding. We demon-

strated empirically that SlotVLA achieves efficient and interpretable visuomotor

control, successfully supporting diverse robotic manipulation tasks with as few as

four slots.

Limitations. Despite its strengths, SlotVLA underperforms on Fine-Target

81

and Long-Horizon tasks compared to Prominent tasks, largely because the pre-

trained visual encoders struggles with small objects and occlusions. We believe

this can be mitigated by improved data augmentation during pre-training or uti-

lize better pretrained visual encoders. Although the proposed temporal sampling

effectively maintains slot consistency, SlotVLA cannot recover from failures, sug-

gesting the need for a memory mechanism in future work.

Broader Impacts. Although SlotVLA is relatively simple, its relation-

centric slot mechanism can potentially be integrated into existing object-centric

VLA frameworks to further enhance effectiveness and interpretability.

82

5

Conclusions and Future Work

5.1 Conclusions

This thesis addressed three fundamental challenges in multimodal robotic

perception and reasoning: enhancing structural biases in unimodal visual models,

achieving efficient semantic mapping for 3D scenes, and developing relationally

grounded visual representations for action-driven tasks. Together, these contribu-

tions advance structured multimodal learning pipelines, making them more prac-

tical and transparent for real-world robotic systems.

Summary of Contributions

1. Proposed AerialFormer, a hybrid Transformer-CNN architecture tailored

for semantic segmentation of aerial imagery. By jointly capturing global

context and fine-grained details, AerialFormer improved the quality of visual

representations and achieved state-of-the-art performance across diverse re-

mote sensing benchmarks.

2. Introduced Open-Fusion, a real-time open-vocabulary 3D scene reconstruc-

tion framework that addresses the need for scalable, queryable 3D represen-

tations. By integrating region-based VL embeddings with TSDF mapping,

Open-Fusion enables zero-shot semantic understanding with efficient storage

and computation.

3. Presented SlotVLA, a compact and interpretable visual tokenization strat-

egy for VLA modeling. SlotVLA reduces token redundancy by focusing on

functional object relations, leading to more efficient and generalizable visuo-

motor control across manipulation tasks.

83

5.2 Future Work

There are several promising directions for future research that can further

extend our contributions to VLA modeling. One important avenue is improv-

ing the deployment of VLA models in real-world robotic arm manipulation tasks.

Although recent VLA approaches have shown encouraging results, most models

operate at relatively low control frequencies, typically around 10Hz, imposing sig-

nificant limitations for high-speed, fine-grained interactions, especially in dynamic

environments.

In many practical applications, robots are equipped with either

third-person or wrist-mounted cameras to perceive their surroundings and execute

visuomotor commands. However, the use of large VL models often requires process-

ing high-resolution images or multiple views, which can bottleneck the inference

speed and reduce the responsiveness of the system.

Future work will focus on improving the efficiency of inference and the

stability of action prediction, with the goal of supporting higher control rates

that meet the latency and throughput demands of real-world systems. This may

involve designing lightweight visual tokenization strategies, improving the temporal

consistency of relational representations, and exploring joint optimization with

low-level control policies.

84

Bibliography

[1] K. He, X. Zhang, S. Ren, and J. Sun, “Deep residual learning for image

recognition. corr abs/1512.03385 (2015),” 2015.

[2] O. Ronneberger, P. Fischer, and T. Brox, “U-net: Convolutional net-
works for biomedical image segmentation,” in Medical Image Computing and
Computer-Assisted Intervention–MICCAI 2015: 18th International Con-
ference, Munich, Germany, October 5-9, 2015, Proceedings, Part III 18.
Springer, 2015, pp. 234–241.

[3] L.-C. Chen, G. Papandreou, F. Schroff, and H. Adam, “Rethinking
atrous convolution for semantic image segmentation,” arXiv preprint
arXiv:1706.05587, 2017.

[4] A. Dosovitskiy, L. Beyer, A. Kolesnikov, D. Weissenborn, X. Zhai, T. Un-
terthiner, M. Dehghani, M. Minderer, G. Heigold, S. Gelly et al., “An image
is worth 16x16 words: Transformers for image recognition at scale,” in In-
ternational Conference on Learning Representations, 2021.

[5] A. Radford, J. W. Kim, C. Hallacy, A. Ramesh, G. Goh, S. Agarwal, G. Sas-
try, A. Askell, P. Mishkin, J. Clark et al., “Learning transferable visual
models from natural language supervision,” in International conference on
machine learning. PMLR, 2021, pp. 8748–8763.

[6] J.-B. Alayrac, J. Donahue, P. Luc, A. Miech, I. Barr, Y. Hasson, K. Lenc,
A. Mensch, K. Millican, M. Reynolds et al., “Flamingo: a visual language
model for few-shot learning,” Advances in neural information processing sys-
tems, vol. 35, pp. 23 716–23 736, 2022.

[7] J. Li, D. Li, C. Xiong, and S. Hoi, “Blip: Bootstrapping language-image
pre-training for unified vision-language understanding and generation,” in
International Conference on Machine Learning. PMLR, 2022, pp. 12 888–
12 900.

[8] G. J. Schumann, G. R. Brakenridge, A. J. Kettner, R. Kashif, and
E. Niebuhr, “Assisting flood disaster response with earth observation data
and products: A critical assessment,” Remote Sensing, vol. 10, no. 8, p. 1230,
2018.

85

[9] M. Weiss, F. Jacob, and G. Duveiller, “Remote sensing for agricultural ap-
plications: A meta-review,” Remote sensing of environment, vol. 236, p.
111402, 2020.

[10] D. Griffiths and J. Boehm, “Improving public data for building segmentation
from convolutional neural networks (cnns) for fused airborne lidar and image
data using active contours,” ISPRS Journal of Photogrammetry and Remote
Sensing, vol. 154, pp. 70–83, 2019.

[11] P. Shamsolmoali, M. Zareapoor, H. Zhou, R. Wang, and J. Yang, “Road
segmentation for remote sensing images using adversarial spatial pyramid
networks,” IEEE Transactions on Geoscience and Remote Sensing, vol. 59,
no. 6, pp. 4673–4688, 2020.

[12] A. Samie, A. Abbas, M. M. Azeem, S. Hamid, M. A. Iqbal, S. S. Hasan,
and X. Deng, “Examining the impacts of future land use/land cover changes
on climate in punjab province, pakistan: implications for environmental sus-
tainability and economic growth,” Environmental Science and Pollution Re-
search, vol. 27, pp. 25 415–25 433, 2020.

[13] D. Marcos, M. Volpi, B. Kellenberger, and D. Tuia, “Land cover mapping
at very high resolution with rotation equivariant cnns: Towards small yet
accurate models,” ISPRS journal of photogrammetry and remote sensing,
vol. 145, pp. 96–107, 2018.

[14] J. Xia, N. Yokoya, B. Adriano, and C. Broni-Bediako, “Openearthmap: A
benchmark dataset for global high-resolution land cover mapping,” in Pro-
ceedings of the IEEE/CVF Winter Conference on Applications of Computer
Vision, 2023, pp. 6254–6264.

“Loveda:
[15] J. Wang, Z. Zheng, A. Ma, X. Lu,
for domain adaptive semantic
A remote sensing land-cover dataset
Information Processing
segmentation,” in Proceedings of
J. Vanschoren and
Systems Track on Datasets and Benchmarks,
S. Yeung, Eds., vol. 1. Curran Associates,
[Online].
Inc.,
Available: https://datasets-benchmarks-proceedings.neurips.cc/paper files/
paper/2021/file/4e732ced3463d06de0ca9a15b6153677-Paper-round2.pdf

and Y. Zhong,

the Neural

2021.

[16] S. J. O’neill, M. Boykoff, S. Niemeyer, and S. A. Day, “On the use of imagery
for climate change engagement,” Global environmental change, vol. 23, no. 2,
pp. 413–421, 2013.

86

[17] R. Andrade, G. Costa, G. Mota, M. Ortega, R. Feitosa, P. Soto, and
C. Heipke, “Evaluation of semantic segmentation methods for deforestation
detection in the amazon,” ISPRS Archives; 43, B3, vol. 43, no. B3, pp.
1497–1505, 2020.

[18] Z. Zheng, Y. Zhong, J. Wang, and A. Ma, “Foreground-aware relation net-
work for geospatial object segmentation in high spatial resolution remote
sensing imagery,” in Proceedings of the IEEE/CVF conference on computer
vision and pattern recognition, 2020, pp. 4096–4105.

[19] A. Shafique, G. Cao, Z. Khan, M. Asad, and M. Aslam, “Deep learning-based
change detection in remote sensing images: A review,” Remote Sensing,
vol. 14, no. 4, p. 871, 2022.

[20] T.-Y. Lin, M. Maire, S. Belongie, J. Hays, P. Perona, D. Ramanan, P. Doll´ar,
and C. L. Zitnick, “Microsoft coco: Common objects in context,” in Com-
puter Vision–ECCV 2014: 13th European Conference, Zurich, Switzerland,
September 6-12, 2014, Proceedings, Part V 13. Springer, 2014, pp. 740–755.

[21] F. Wang, S. Piao, and J. Xie, “Cse-hrnet: A context and semantic enhanced
high-resolution network for semantic segmentation of aerial imagery,” IEEE
Access, vol. 8, pp. 182 475–182 489, 2020.

[22] L. Wang, R. Li, C. Zhang, S. Fang, C. Duan, X. Meng, and P. M. Atkinson,
“Unetformer: A unet-like transformer for efficient semantic segmentation of
remote sensing urban scene imagery,” ISPRS Journal of Photogrammetry
and Remote Sensing, vol. 190, pp. 196–214, 2022.

[23] L. Wang, R. Li, C. Duan, C. Zhang, X. Meng, and S. Fang, “A novel trans-
former based semantic segmentation scheme for fine-resolution remote sens-
ing images,” IEEE Geoscience and Remote Sensing Letters, vol. 19, pp. 1–5,
2022.

[24] S. Minaee, Y. Y. Boykov, F. Porikli, A. J. Plaza, N. Kehtarnavaz, and D. Ter-
zopoulos, “Image segmentation using deep learning: A survey,” IEEE trans-
actions on pattern analysis and machine intelligence, 2021.

[25] N. Le, T. Bui, V.-K. Vo-Ho, K. Yamazaki, and K. Luu, “Narrow band active
contour attention model for medical segmentation,” Diagnostics, vol. 11,
no. 8, p. 1393, 2021.

[26] K. He, X. Zhang, S. Ren, and J. Sun, “Deep residual learning for image
recognition,” in Proceedings of the IEEE conference on computer vision and
pattern recognition, 2016, pp. 770–778.

87

[27] J. Long, E. Shelhamer, and T. Darrell, “Fully convolutional networks for
semantic segmentation,” in Proceedings of the IEEE conference on computer
vision and pattern recognition, 2015, pp. 3431–3440.

[28] L.-C. Chen, G. Papandreou, I. Kokkinos, K. Murphy, and A. L. Yuille,
“Deeplab: Semantic image segmentation with deep convolutional nets, atrous
convolution, and fully connected crfs,” IEEE transactions on pattern analysis
and machine intelligence, vol. 40, no. 4, pp. 834–848, 2017.

[29] J. Dai, H. Qi, Y. Xiong, Y. Li, G. Zhang, H. Hu, and Y. Wei, “Deformable
convolutional networks,” in Proceedings of the IEEE international conference
on computer vision, 2017, pp. 764–773.

[30] L.-C. Chen, Y. Zhu, G. Papandreou, F. Schroff, and H. Adam, “Encoder-
decoder with atrous separable convolution for semantic image segmentation,”
in Proceedings of the European conference on computer vision (ECCV), 2018,
pp. 801–818.

[31] M. Yang, K. Yu, C. Zhang, Z. Li, and K. Yang, “Denseaspp for semantic
segmentation in street scenes,” in Proceedings of the IEEE conference on
computer vision and pattern recognition, 2018, pp. 3684–3692.

[32] D.-H. Hoang, G.-H. Diep, M.-T. Tran, and N. T. H. Le, “Dam-al: Dilated
attention mechanism with attention loss for 3d infant brain image segmen-
tation,” in Proceedings of the 37th ACM/SIGAPP Symposium on Applied
Computing, 2022, pp. 660–668.

[33] N. Le, K. Yamazaki, K. G. Quach, D. Truong, and M. Savvides, “A multi-
task contextual atrous residual network for brain tumor detection & seg-
mentation,” in 2020 25th International Conference on Pattern Recognition
(ICPR).

IEEE, 2021, pp. 5943–5950.

[34] T. H. N. Le, C. N. Duong, L. Han, K. Luu, K. G. Quach, and M. Savvides,
“Deep contextual recurrent residual networks for scene labeling,” Pattern
Recognition, vol. 80, pp. 32–41, 2018.

[35] J. He, Z. Deng, L. Zhou, Y. Wang, and Y. Qiao, “Adaptive pyramid context
network for semantic segmentation,” in Proceedings of the IEEE/CVF Con-
ference on Computer Vision and Pattern Recognition, 2019, pp. 7519–7528.

[36] C.-W. Hsiao, C. Sun, H.-T. Chen, and M. Sun, “Specialize and fuse: Pyrami-
dal output representation for semantic segmentation,” in Proceedings of the
IEEE/CVF International Conference on Computer Vision, 2021, pp. 7137–
7146.

88

[37] H. Hu, D. Ji, W. Gan, S. Bai, W. Wu, and J. Yan, “Class-wise dynamic graph
convolution for semantic segmentation,” in Computer Vision–ECCV 2020:
16th European Conference, Glasgow, UK, August 23–28, 2020, Proceedings,
Part XVII 16. Springer, 2020, pp. 1–17.

[38] Z. Jin, T. Gong, D. Yu, Q. Chu, J. Wang, C. Wang, and J. Shao, “Mining
contextual information beyond image for semantic segmentation,” in Pro-
ceedings of the IEEE/CVF International Conference on Computer Vision,
2021, pp. 7231–7241.

[39] Z. Jin, B. Liu, Q. Chu, and N. Yu, “Isnet: Integrate image-level and semantic-
level context for semantic segmentation,” in Proceedings of the IEEE/CVF
International Conference on Computer Vision, 2021, pp. 7189–7198.

[40] C. Yu, J. Wang, C. Gao, G. Yu, C. Shen, and N. Sang, “Context prior
for scene segmentation,” in Proceedings of the IEEE/CVF conference on
computer vision and pattern recognition, 2020, pp. 12 416–12 425.

[41] Y. Yuan, X. Chen, X. Chen, and J. Wang, “Segmentation trans-
former: Object-contextual representations for semantic segmentation,” arXiv
preprint arXiv:1909.11065, 2019.

[42] H. Zhang, K. Dana, J. Shi, Z. Zhang, X. Wang, A. Tyagi, and A. Agrawal,
“Context encoding for semantic segmentation,” in Proceedings of the IEEE
conference on Computer Vision and Pattern Recognition, 2018, pp. 7151–
7160.

[43] G. Bertasius, J. Shi, and L. Torresani, “Semantic segmentation with bound-
ary neural fields,” in Proceedings of the IEEE conference on computer vision
and pattern recognition, 2016, pp. 3602–3610.

[44] N. Le, T. Le, K. Yamazaki, T. Bui, K. Luu, and M. Savides, “Offset curves
loss for imbalanced problem in medical segmentation,” in 2020 25th Interna-
tional Conference on Pattern Recognition (ICPR).
IEEE, 2021, pp. 9189–
9195.

[45] H. Ding, X. Jiang, A. Q. Liu, N. M. Thalmann, and G. Wang, “Boundary-
aware feature propagation for scene segmentation,” in Proceedings of the
IEEE/CVF International Conference on Computer Vision, 2019, pp. 6819–
6829.

[46] X. Li, X. Li, L. Zhang, G. Cheng, J. Shi, Z. Lin, S. Tan, and Y. Tong, “Im-
proving semantic segmentation via decoupled body and edge supervision,”

89

in Computer Vision–ECCV 2020: 16th European Conference, Glasgow, UK,
August 23–28, 2020, Proceedings, Part XVII 16. Springer, 2020, pp. 435–
452.

[47] M. Zhen, J. Wang, L. Zhou, S. Li, T. Shen, J. Shang, T. Fang, and L. Quan,
“Joint semantic segmentation and boundary detection using iterative pyra-
mid contexts,” in Proceedings of the IEEE/CVF Conference on Computer
Vision and Pattern Recognition, 2020, pp. 13 666–13 675.

[48] A. W. Harley, K. G. Derpanis, and I. Kokkinos, “Segmentation-aware con-
volutional networks using local attention masks,” in Proceedings of the IEEE
International Conference on Computer Vision, 2017, pp. 5038–5047.

[49] J. He, Z. Deng, and Y. Qiao, “Dynamic multi-scale filters for semantic seg-
mentation,” in Proceedings of the IEEE/CVF International Conference on
Computer Vision, 2019, pp. 3562–3572.

[50] H. Zhao, Y. Zhang, S. Liu, J. Shi, C. C. Loy, D. Lin, and J. Jia, “Psanet:
Point-wise spatial attention network for scene parsing,” in Proceedings of the
European conference on computer vision (ECCV), 2018, pp. 267–283.

[51] J. Hu, L. Shen, and G. Sun, “Squeeze-and-excitation networks,” in Pro-
ceedings of the IEEE conference on computer vision and pattern recognition,
2018, pp. 7132–7141.

[52] Z. Huang, X. Wang, L. Huang, C. Huang, Y. Wei, and W. Liu, “Ccnet: Criss-
cross attention for semantic segmentation,” in Proceedings of the IEEE/CVF
international conference on computer vision, 2019, pp. 603–612.

[53] H. Li, P. Xiong, J. An, and L. Wang, “Pyramid attention network for se-

mantic segmentation,” arXiv preprint arXiv:1805.10180, 2018.

[54] G. Sun, W. Wang, J. Dai, and L. Van Gool, “Mining cross-image semantics
for weakly supervised semantic segmentation,” in Computer Vision–ECCV
2020: 16th European Conference, Glasgow, UK, August 23–28, 2020, Pro-
ceedings, Part II 16. Springer, 2020, pp. 347–365.

[55] W. Wang, T. Zhou, S. Qi, J. Shen, and S.-C. Zhu, “Hierarchical human
semantic parsing with comprehensive part-relation modeling,” IEEE Trans-
actions on Pattern Analysis and Machine Intelligence, vol. 44, no. 7, pp.
3508–3522, 2021.

90

[56] X. Wang, R. Girshick, A. Gupta, and K. He, “Non-local neural networks,”
in Proceedings of the IEEE conference on computer vision and pattern recog-
nition, 2018, pp. 7794–7803.

[57] N. Carion, F. Massa, G. Synnaeve, N. Usunier, A. Kirillov, and S. Zagoruyko,
“End-to-end object detection with transformers,” in Computer Vision–
ECCV 2020: 16th European Conference, Glasgow, UK, August 23–28, 2020,
Proceedings, Part I 16. Springer, 2020, pp. 213–229.

[58] S. Liu, F. Li, H. Zhang, X. Yang, X. Qi, H. Su, J. Zhu, and L. Zhang, “Dab-
detr: Dynamic anchor boxes are better queries for detr,” arXiv preprint
arXiv:2201.12329, 2022.

[59] F. Li, H. Zhang, S. Liu, J. Guo, L. M. Ni, and L. Zhang, “Dn-detr: Ac-
celerate detr training by introducing query denoising,” in Proceedings of the
IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2022,
pp. 13 619–13 627.

[60] A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez,
(cid:32)L. Kaiser, and I. Polosukhin, “Attention is all you need,” Advances in neural
information processing systems, vol. 30, 2017.

[61] B. Cheng, A. Schwing, and A. Kirillov, “Per-pixel classification is not all you
need for semantic segmentation,” Advances in Neural Information Processing
Systems, vol. 34, pp. 17 864–17 875, 2021.

[62] R. Strudel, R. Garcia, I. Laptev, and C. Schmid, “Segmenter: Transformer
for semantic segmentation,” in Proceedings of the IEEE/CVF international
conference on computer vision, 2021, pp. 7262–7272.

[63] S. Zheng, J. Lu, H. Zhao, X. Zhu, Z. Luo, Y. Wang, Y. Fu, J. Feng, T. Xiang,
P. H. Torr et al., “Rethinking semantic segmentation from a sequence-to-
sequence perspective with transformers,” in Proceedings of the IEEE/CVF
conference on computer vision and pattern recognition, 2021, pp. 6881–6890.

[64] E. Xie, W. Wang, Z. Yu, A. Anandkumar, J. M. Alvarez, and P. Luo, “Seg-
former: Simple and efficient design for semantic segmentation with trans-
formers,” Advances in Neural Information Processing Systems, vol. 34, pp.
12 077–12 090, 2021.

[65] M. Tran, K. Vo, K. Yamazaki, A. Fernandes, M. Kidd, and N. Le, “Aisformer:
Amodal instance segmentation with transformer,” British Machine Vision
Conference (BMVC), 2022.

91

[66] B. Cheng, I. Misra, A. G. Schwing, A. Kirillov, and R. Girdhar, “Masked-
attention mask transformer for universal image segmentation,” in Proceedings
of the IEEE/CVF Conference on Computer Vision and Pattern Recognition,
2022, pp. 1290–1299.

[67] H. Touvron, M. Cord, M. Douze, F. Massa, A. Sablayrolles, and H. J´egou,
“Training data-efficient image transformers & distillation through attention,”
in International conference on machine learning. PMLR, 2021, pp. 10 347–
10 357.

[68] X. Zhu, W. Su, L. Lu, B. Li, X. Wang, and J. Dai, “Deformable detr:
Deformable transformers for end-to-end object detection,” arXiv preprint
arXiv:2010.04159, 2020.

[69] P. Sun, R. Zhang, Y. Jiang, T. Kong, C. Xu, W. Zhan, M. Tomizuka, L. Li,
Z. Yuan, C. Wang et al., “Sparse r-cnn: End-to-end object detection with
learnable proposals,” in Proceedings of the IEEE/CVF conference on com-
puter vision and pattern recognition, 2021, pp. 14 454–14 463.

[70] L. Ye, M. Rochan, Z. Liu, and Y. Wang, “Cross-modal self-attention network
for referring image segmentation,” in Proceedings of the IEEE/CVF confer-
ence on computer vision and pattern recognition, 2019, pp. 10 502–10 511.

[71] K. Vo, H. Joo, K. Yamazaki, S. Truong, K. Kitani, M.-T. Tran, and N. Le,
“AEI: Actors-Environment Interaction with Adaptive Attention for Tempo-
ral Action Proposals Generation,” BMVC, 2021.

[72] K. Vo, S. Truong, K. Yamazaki, B. Raj, M.-T. Tran, and N. Le, “Aoe-
net: Entities interactions modeling with adaptive attention mechanism for
temporal action proposals generation,” International Journal of Computer
Vision, pp. 1–22, 2022.

[73] K. Yamazaki, S. Truong, K. Vo, M. Kidd, C. Rainwater, K. Luu, and N. Le,
“Vlcap: Vision-language with contrastive learning for coherent video para-
graph captioning,” in 2022 IEEE International Conference on Image Pro-
cessing (ICIP).

IEEE, 2022, pp. 3656–3661.

[74] K. Yamazaki, K. Vo, S. Truong, B. Raj, and N. Le, “Vltint: Visual-linguistic
transformer-in-transformer for coherent video paragraph captioning,” The
Thirty-Seventh AAAI Conference on Artificial Intelligence, 2023.

[75] K. Sun, B. Xiao, D. Liu, and J. Wang, “Deep high-resolution representa-
tion learning for human pose estimation,” in Proceedings of the IEEE/CVF
conference on computer vision and pattern recognition, 2019, pp. 5693–5703.

92

[76] X. Li, H. He, X. Li, D. Li, G. Cheng, J. Shi, L. Weng, Y. Tong, and Z. Lin,
“Pointflow: Flowing semantics through points for aerial image segmenta-
tion,” in Proceedings of the IEEE/CVF Conference on Computer Vision and
Pattern Recognition, 2021, pp. 4217–4226.

[77] G. Xue, Y. Liu, Y. Huang, M. Li, and G. Yang, “Aanet: an attention-based
alignment semantic segmentation network for high spatial resolution remote
sensing images,” International Journal of Remote Sensing, vol. 43, no. 13,
pp. 4836–4852, 2022.

[78] A. Ma, J. Wang, Y. Zhong, and Z. Zheng, “Factseg: Foreground activation-
driven small object semantic segmentation in large-scale remote sensing im-
agery,” IEEE Transactions on Geoscience and Remote Sensing, vol. 60, pp.
1–16, 2022.

[79] J. Hou, Z. Guo, Y. Wu, W. Diao, and T. Xu, “Bsnet: Dynamic hybrid
gradient convolution based boundary-sensitive network for remote sensing
image segmentation,” IEEE Transactions on Geoscience and Remote Sens-
ing, vol. 60, pp. 1–22, 2022.

[80] H. You, S. Tian, L. Yu, and Y. Lv, “Pixel-level remote sensing image recogni-
tion based on bidirectional word vectors,” IEEE Transactions on Geoscience
and Remote Sensing, vol. 58, no. 2, pp. 1281–1293, 2019.

[81] L. Mou, Y. Hua, and X. X. Zhu, “Relation matters: Relational context-aware
fully convolutional network for semantic segmentation of high-resolution
images,” IEEE Transactions on Geoscience and Remote Sensing,
aerial
vol. 58, no. 11, pp. 7557–7569, 2020.

[82] R. Niu, X. Sun, Y. Tian, W. Diao, K. Chen, and K. Fu, “Hybrid multiple
attention network for semantic segmentation in aerial images,” IEEE Trans-
actions on Geoscience and Remote Sensing, vol. 60, pp. 1–18, 2021.

[83] D. Wang, J. Zhang, B. Du, G.-S. Xia, and D. Tao, “An empirical study of
remote sensing pretraining,” IEEE Transactions on Geoscience and Remote
Sensing, 2022.

[84] R. Xu, C. Wang, J. Zhang, S. Xu, W. Meng, and X. Zhang, “Rssformer:
Foreground saliency enhancement for remote sensing land-cover segmenta-
tion,” IEEE Transactions on Image Processing, vol. 32, pp. 1052–1064, 2023.

[85] J. Chen, Y. Lu, Q. Yu, X. Luo, E. Adeli, Y. Wang, L. Lu, A. L. Yuille, and
Y. Zhou, “Transunet: Transformers make strong encoders for medical image
segmentation,” arXiv preprint arXiv:2102.04306, 2021.

93

[86] X. Sun, P. Wang, W. Lu, Z. Zhu, X. Lu, Q. He, J. Li, X. Rong, Z. Yang,
H. Chang et al., “Ringmo: A remote sensing foundation model with masked
image modeling,” IEEE Transactions on Geoscience and Remote Sensing,
2022.

[87] S. Ioffe and C. Szegedy, “Batch normalization: Accelerating deep network
training by reducing internal covariate shift,” in International conference on
machine learning. pmlr, 2015, pp. 448–456.

[88] D. Hendrycks and K. Gimpel, “Gaussian error linear units (gelus),” arXiv

preprint arXiv:1606.08415, 2016.

[89] Z. Liu, Y. Lin, Y. Cao, H. Hu, Y. Wei, Z. Zhang, S. Lin, and B. Guo,
“Swin transformer: Hierarchical vision transformer using shifted windows,”
in Proceedings of the IEEE/CVF international conference on computer vi-
sion, 2021, pp. 10 012–10 022.

[90] J. L. Ba, J. R. Kiros, and G. E. Hinton, “Layer normalization,” arXiv

preprint arXiv:1607.06450, 2016.

[91] S. Waqas Zamir, A. Arora, A. Gupta, S. Khan, G. Sun, F. Shahbaz Khan,
F. Zhu, L. Shao, G.-S. Xia, and X. Bai, “isaid: A large-scale dataset for
instance segmentation in aerial images,” in Proceedings of the IEEE/CVF
Conference on Computer Vision and Pattern Recognition Workshops, 2019,
pp. 28–37.

[92] “2d semantic labeling contest

- potsdam,” International Society for
Photogrammetry and Remote Sensing. [Online]. Available: https://www.
isprs.org/education/benchmarks/UrbanSemLab/default.aspx

[93] X. He, Y. Zhou, J. Zhao, D. Zhang, R. Yao, and Y. Xue, “Swin transformer
embedding unet for remote sensing image semantic segmentation,” IEEE
Transactions on Geoscience and Remote Sensing, vol. 60, pp. 1–15, 2022.

[94] D. P. Kingma and J. Ba, “Adam: A method for stochastic optimization,”

arXiv preprint arXiv:1412.6980, 2014.

[95] J. Deng, W. Dong, R. Socher, L.-J. Li, K. Li, and L. Fei-Fei, “Imagenet: A
large-scale hierarchical image database,” in 2009 IEEE conference on com-
puter vision and pattern recognition.

Ieee, 2009, pp. 248–255.

[96] H. Zhao, J. Shi, X. Qi, X. Wang, and J. Jia, “Pyramid scene parsing net-
work,” in Proceedings of the IEEE conference on computer vision and pattern
recognition, 2017, pp. 2881–2890.

94

[97] G. Liu, Q. Wang, J. Zhu, and H. Hong, “W-net: Convolutional neural net-
work for segmenting remote sensing images by dual path semantics,” Plos
one, vol. 18, no. 7, p. e0288311, 2023.

[98] Z. Zheng, Y. Zhong, J. Wang, A. Ma, and L. Zhang, “Farseg++: Foreground-
aware relation network for geospatial object segmentation in high spatial
resolution remote sensing imagery,” IEEE Transactions on Pattern Analysis
and Machine Intelligence, 2023.

[99] Z. Gong, L. Duan, F. Xiao, and Y. Wang, “Msaug: Multi-strategy augmen-
tation for rare classes in semantic segmentation of remote sensing images,”
Displays, p. 102779, 2024.

[100] S. He, C. Jin, L. Shu, X. He, M. Wang, and G. Liu, “A new framework for
improving semantic segmentation in aerial imagery,” Frontiers in Remote
Sensing, vol. 5, p. 1370697, 2024.

[101] H. Li, K. Qiu, L. Chen, X. Mei, L. Hong, and C. Tao, “Scattnet: Seman-
tic segmentation network with spatial and channel attention mechanism for
high-resolution remote sensing images,” IEEE Geoscience and Remote Sens-
ing Letters, vol. 18, no. 5, pp. 905–909, 2020.

[102] Y. Long, G.-S. Xia, S. Li, W. Yang, M. Y. Yang, X. X. Zhu, L. Zhang,
and D. Li, “On creating benchmark dataset for aerial image interpretation:
Reviews, guidances, and million-aid,” IEEE Journal of selected topics in
applied earth observations and remote sensing, vol. 14, pp. 4205–4230, 2021.

[103] T. Xiao, Y. Liu, B. Zhou, Y. Jiang, and J. Sun, “Unified perceptual pars-
ing for scene understanding,” in Proceedings of the European Conference on
computer vision (ECCV), 2018, pp. 418–434.

[104] J. Fu, J. Liu, H. Tian, Y. Li, Y. Bao, Z. Fang, and H. Lu, “Dual attention
network for scene segmentation,” in Proceedings of the IEEE/CVF conference
on computer vision and pattern recognition, 2019, pp. 3146–3154.

[105] X. Li, Z. Zhong, J. Wu, Y. Yang, Z. Lin, and H. Liu, “Expectation-
maximization attention networks for semantic segmentation,” in Proceedings
of the IEEE/CVF International Conference on Computer Vision, 2019, pp.
9167–9176.

[106] X. Ma, M. Ma, C. Hu, Z. Song, Z. Zhao, T. Feng, and W. Zhang, “Log-
can:
local-global class-aware network for semantic segmentation of remote
sensing images,” in ICASSP 2023-2023 IEEE International Conference on
Acoustics, Speech and Signal Processing (ICASSP).

IEEE, 2023, pp. 1–5.

95

[107] L. Sun, H. Zou, J. Wei, X. Cao, S. He, M. Li, and S. Liu, “Semantic segmen-
tation of high-resolution remote sensing images based on sparse self-attention
and feature alignment,” Remote Sensing, vol. 15, no. 6, p. 1598, 2023.

[108] T. Wang, C. Xu, B. Liu, G. Yang, E. Zhang, D. Niu, and H. Zhang, “Mcat-
unet: Convolutional and cross-shaped window attention enhanced unet for
efficient high-resolution remote sensing image segmentation,” IEEE Journal
of Selected Topics in Applied Earth Observations and Remote Sensing, 2024.

[109] L. Ding, H. Tang, and L. Bruzzone, “Lanet: Local attention embedding to
improve the semantic segmentation of remote sensing images,” IEEE Trans-
actions on Geoscience and Remote Sensing, vol. 59, no. 1, pp. 426–435, 2020.

[110] Q. Xu, X. Yuan, C. Ouyang, and Y. Zeng, “Spatial–spectral ffpnet:
Attention-based pyramid network for segmentation and classification of re-
mote sensing images,” arXiv preprint arXiv:2008.08775, 2020.

[111] Q. Zhang and Y.-B. Yang, “Rest: An efficient transformer for visual recog-
nition,” Advances in Neural Information Processing Systems, vol. 34, pp.
15 475–15 485, 2021.

[112] R. Li, S. Zheng, C. Zhang, C. Duan, L. Wang, and P. M. Atkinson, “Abcnet:
Attentive bilateral contextual network for efficient semantic segmentation of
fine-resolution remotely sensed imagery,” ISPRS Journal of Photogrammetry
and Remote Sensing, vol. 181, pp. 84–98, 2021.

[113] Y. Chen, P. Fang, J. Yu, X. Zhong, X. Zhang, and T. Li, “Hi-resnet: A
high-resolution remote sensing network for semantic segmentation,” arXiv
preprint arXiv:2305.12691, 2023.

[114] L. Wang, S. Dong, Y. Chen, X. Meng, and S. Fang, “Metasegnet: Metadata-
collaborative vision-language representation learning for semantic segmenta-
tion of remote sensing images,” arXiv preprint arXiv:2312.12735, 2023.

[115] X. Zhang, Z. Weng, P. Zhu, X. Han, J. Zhu, and L. Jiao, “Esdinet: Effi-
cient shallow-deep interaction network for semantic segmentation of high-
resolution aerial images,” IEEE Transactions on Geoscience and Remote
Sensing, 2024.

[116] A. Chaurasia and E. Culurciello, “Linknet: Exploiting encoder representa-
tions for efficient semantic segmentation,” in 2017 IEEE visual communica-
tions and image processing (VCIP).

IEEE, 2017, pp. 1–4.

96

[117] V. Badrinarayanan, A. Kendall, and R. Cipolla, “Segnet: A deep convolu-
tional encoder-decoder architecture for image segmentation,” IEEE trans-
actions on pattern analysis and machine intelligence, vol. 39, no. 12, pp.
2481–2495, 2017.

[118] Z. Zhou, M. M. Rahman Siddiquee, N. Tajbakhsh, and J. Liang, “Unet++:
A nested u-net architecture for medical image segmentation,” in Deep Learn-
ing in Medical Image Analysis and Multimodal Learning for Clinical Deci-
sion Support: 4th International Workshop, DLMIA 2018, and 8th Interna-
tional Workshop, ML-CDS 2018, Held in Conjunction with MICCAI 2018,
Granada, Spain, September 20, 2018, Proceedings 4.
Springer, 2018, pp.
3–11.

[119] D. Wang, Q. Zhang, Y. Xu, J. Zhang, B. Du, D. Tao, and L. Zhang, “Ad-
vancing plain vision transformer towards remote sensing foundation model,”
IEEE Transactions on Geoscience and Remote Sensing, 2022.

[120] B. Liu and Z. Zhong, “Gdformer: a lightweight decoder for efficient semantic
segmentation of remote sensing urban scene imagery,” in Fourth Interna-
tional Conference on Computer Vision and Data Mining (ICCVDM 2023),
vol. 13063. SPIE, 2024, pp. 149–154.

[121] H. Cao, Y. Wang, J. Chen, D. Jiang, X. Zhang, Q. Tian, and M. Wang,
“Swin-unet: Unet-like pure transformer for medical image segmentation,” in
Computer Vision–ECCV 2022 Workshops: Tel Aviv, Israel, October 23–27,
2022, Proceedings, Part III. Springer, 2023, pp. 205–218.

[122] S. Song, S. P. Lichtenberg, and J. Xiao, “Sun rgb-d: A rgb-d scene un-
derstanding benchmark suite,” in Proceedings of the IEEE conference on
computer vision and pattern recognition, 2015, pp. 567–576.

[123] M. Naseer, S. Khan, and F. Porikli, “Indoor scene understanding in 2.5/3d
for autonomous agents: A survey,” IEEE access, vol. 7, pp. 1859–1887, 2018.

[124] C. Jia, Y. Yang, Y. Xia et al., “Scaling up visual and vision-language rep-
resentation learning with noisy text supervision,” in ICLR. PMLR, 2021,
pp. 4904–4916.

[125] L. H. Li, P. Zhang, H. Zhang, J. Yang, C. Li, Y. Zhong, L. Wang, L. Yuan,
L. Zhang, J.-N. Hwang et al., “Grounded language-image pre-training,” in
Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern
Recognition, 2022, pp. 10 965–10 975.

97

[126] Y. Zhong, J. Yang et al., “Regionclip: Region-based language-image pre-

training,” in CVPR, 2022, pp. 16 793–16 803.

[127] S. Y. Gadre, M. Wortsman, G. Ilharco, L. Schmidt, and S. Song, “Cows on
pasture: Baselines and benchmarks for language-driven zero-shot object nav-
igation,” in Proceedings of the IEEE/CVF Conference on Computer Vision
and Pattern Recognition, 2023, pp. 23 171–23 181.

[128] R. Selvaraju, M. Cogswell, A. Das, R. Vedantam, D. Parikh, and D. Ba-
tra, “Grad-cam: Visual explanations from deep networks via gradient-based
localization. arxiv 2016,” arXiv preprint arXiv:1610.02391, 2022.

[129] B. Chen, F. Xia, B. Ichter, K. Rao, K. Gopalakrishnan, M. S. Ryoo, A. Stone,
and D. Kappler, “Open-vocabulary queryable scene representations for real
world planning,” in 2023 IEEE International Conference on Robotics and
IEEE, 2023, pp. 11 509–11 522.
Automation (ICRA).

[130] X. Gu, T.-Y. Lin, W. Kuo, and Y. Cui, “Open-vocabulary object de-
tection via vision and language knowledge distillation,” arXiv preprint
arXiv:2104.13921, 2021.

[131] C. Huang, O. Mees, A. Zeng, and W. Burgard, “Visual language maps for
robot navigation,” in 2023 IEEE International Conference on Robotics and
IEEE, 2023, pp. 10 608–10 615.
Automation (ICRA).

[132] B. Li, K. Q. Weinberger, S. Belongie, V. Koltun, and R. Ranftl, “Language-
driven Semantic Segmentation,” arXiv e-prints, p. arXiv:2201.03546, Jan.
2022.

[133] N. M. M. Shafiullah, C. Paxton, L. Pinto, S. Chintala, and A. Szlam, “Clip-
fields: Weakly supervised semantic fields for robotic memory,” arXiv preprint
arXiv:2210.05663, 2022.

[134] X. Zhou, R. Girdhar, A. Joulin, P. Kr¨ahenb¨uhl, and I. Misra, “Detecting
twenty-thousand classes using image-level supervision,” in European Confer-
ence on Computer Vision. Springer, 2022, pp. 350–368.

[135] J. Kerr, C. M. Kim, K. Goldberg, A. Kanazawa, and M. Tancik, “Lerf:
Language embedded radiance fields,” arXiv preprint arXiv:2303.09553, 2023.

[136] H. Ha and S. Song, “Semantic abstraction: Open-world 3d scene understand-
ing from 2d vision-language models,” in 6th Annual Conference on Robot
Learning, 2022.

98

[137] K. M. Jatavallabhula, A. Kuwajerwala, Q. Gu, M. Omama, T. Chen, S. Li,
G. Iyer, S. Saryazdi, N. Keetha, A. Tewari et al., “Conceptfusion: Open-set
multimodal 3d mapping,” arXiv preprint arXiv:2302.07241, 2023.

[138] A. Kirillov, E. Mintun, N. Ravi, H. Mao, C. Rolland, L. Gustafson, T. Xiao,
S. Whitehead, A. C. Berg, W.-Y. Lo et al., “Segment anything,” arXiv
preprint arXiv:2304.02643, 2023.

[139] X. Zou, J. Yang, H. Zhang, F. Li, L. Li, J. Gao, and Y. J. Lee, “Segment
everything everywhere all at once,” arXiv preprint arXiv:2304.06718, 2023.

[140] J. Yang, C. Li et al., “Unified contrastive learning in image-text-label space,”

in CVPR, 2022, pp. 19 163–19 173.

[141] J. Li, D. Li, S. Savarese, and S. Hoi, “Blip-2: Bootstrapping language-image
pre-training with frozen image encoders and large language models,” arXiv
preprint arXiv:2301.12597, 2023.

[142] C. Zhou, C. C. Loy, and B. Dai, “Extract free dense labels from clip,” in

European Conference on Computer Vision. Springer, 2022, pp. 696–712.

[143] H. Zhang, P. Zhang et al., “Glipv2: Unifying localization and vision-language

understanding,” NIPS, 2022.

[144] J. Xu, S. Liu, A. Vahdat, W. Byeon, X. Wang, and S. De Mello, “Open-
vocabulary panoptic segmentation with text-to-image diffusion models,” in
Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern
Recognition, 2023, pp. 2955–2966.

[145] X. Wang, S. Li, K. Kallidromitis, Y. Kato, K. Kozuka, and T. Darrell, “Hi-
erarchical open-vocabulary universal image segmentation,” arXiv preprint
arXiv:2307.00764, 2023.

[146] F. Li, H. Zhang, P. Sun, X. Zou, S. Liu, J. Yang, C. Li, L. Zhang, and J. Gao,
“Semantic-sam: Segment and recognize anything at any granularity,” arXiv
preprint arXiv:2307.04767, 2023.

[147] N. Reimers and I. Gurevych, “Sentence-bert: Sentence embeddings using

siamese bert-networks,” arXiv preprint arXiv:1908.10084, 2019.

[148] W. Dong, J. Park, Y. Yang, and M. Kaess, “Gpu accelerated robust scene
reconstruction,” in 2019 IEEE/RSJ International Conference on Intelligent
Robots and Systems (IROS).

IEEE, 2019, pp. 7863–7870.

99

[149] Y. Huang, Z. Tang, D. Chen, K. Su, and C. Chen, “Batching soft iou for
training semantic segmentation networks,” IEEE Signal Processing Letters,
vol. 27, pp. 66–70, 2019.

[150] D. F. Crouse, “On implementing 2d rectangular assignment algorithms,”
IEEE Transactions on Aerospace and Electronic Systems, vol. 52, no. 4, pp.
1679–1696, 2016.

[151] A. Dai, A. X. Chang, M. Savva, M. Halber, T. Funkhouser, and M. Nießner,
“Scannet: Richly-annotated 3d reconstructions of indoor scenes,” in Pro-
ceedings of the IEEE conference on computer vision and pattern recognition,
2017, pp. 5828–5839.

[152] J. Straub, T. Whelan, L. Ma, Y. Chen, E. Wijmans, S. Green, J. J. Engel,
R. Mur-Artal, C. Ren, S. Verma et al., “The replica dataset: A digital replica
of indoor spaces,” arXiv preprint arXiv:1906.05797, 2019.

[153] N. Hirose, C. Glossop, A. Sridhar, O. Mees, and S. Levine, “Lelan: Learn-
ing a language-conditioned navigation policy from in-the-wild video,” in 8th
Annual Conference on Robot Learning, 2024.

[154] J. H. Yang, C. Glossop, A. Bhorkar, D. Shah, Q. Vuong, C. Finn, D. Sadigh,
and S. Levine, “Pushing the limits of cross-embodiment learning for manip-
ulation and navigation,” in Robotics: Science and Systems (RSS), 2024.

[155] Octo Model Team, D. Ghosh, H. Walke, K. Pertsch, K. Black, O. Mees,
S. Dasari, J. Hejna, C. Xu, J. Luo, T. Kreiman, Y. Tan, P. Sanketi, Q. Vuong,
T. Xiao, D. Sadigh, C. Finn, and S. Levine, “Octo: An open-source gener-
alist robot policy,” in Proceedings of Robotics: Science and Systems, Delft,
Netherlands, 2024.

[156] M. J. Kim, K. Pertsch, S. Karamcheti, T. Xiao, A. Balakrishna, S. Nair,
R. Rafailov, E. P. Foster, P. R. Sanketi, Q. Vuong, T. Kollar, B. Burchfiel,
R. Tedrake, D. Sadigh, S. Levine, P. Liang, and C. Finn, “Openvla: An
open-source vision-language-action model,” in Proceedings of The 8th Con-
ference on Robot Learning, ser. Proceedings of Machine Learning Research,
P. Agrawal, O. Kroemer, and W. Burgard, Eds., vol. 270. PMLR, 06–09
Nov 2025, pp. 2679–2713.

[157] X. Li, M. Liu, H. Zhang, C. Yu, J. Xu, H. Wu, C. Cheang, Y. Jing, W. Zhang,
H. Liu, H. Li, and T. Kong, “Vision-language foundation models as effective
robot imitators,” in International Conference on Learning Representations
(ICLR), 2024.

100

[158] H. Bharadhwaj, J. Vakil, M. Sharma, A. Gupta, S. Tulsiani, and V. Kumar,
“Roboagent: Generalization and efficiency in robot manipulation via seman-
tic augmentations and action chunking,” in IEEE International Conference
on Robotics and Automation (ICRA), 2024.

[159] A. Brohan, N. Brown, J. Carbajal, Y. Chebotar et al., “RT-1: robotics
transformer for real-world control at scale,” in Robotics: Science and Systems
(RSS), 2023.

[160] Y. Ma, Z. Song, Y. Zhuang, J. Hao, and I. King, “A survey on vision-
language-action models for embodied ai,” CoRR, vol. abs/2405.14093, 2024.

[161] J. Hwang, R. Xu, H. Lin, W. Hung, J. Ji, K. Choi, D. Huang, T. He, P. Cov-
ington, B. Sapp, J. Guo, D. Anguelov, and M. Tan, “EMMA: end-to-end mul-
timodal model for autonomous driving,” CoRR, vol. abs/2410.23262, 2024.

[162] M. Zawalski, W. Chen, K. Pertsch, O. Mees, C. Finn, and S. Levine, “Robotic
control via embodied chain-of-thought reasoning,” in Conference on Robot
Learning (CoRL), 2024.

[163] L. Wang, X. Chen, J. Zhao, and K. He, “Scaling proprioceptive-visual learn-
ing with heterogeneous pre-trained transformers,” in Advances in Neural
Information Processing Systems (NeurIPS), 2024.

[164] M. Oquab, T. Darcet, T. Moutakanni, H. V. Vo, M. Szafraniec, V. Khali-
dov, P. Fernandez, D. HAZIZA, F. Massa, A. El-Nouby, M. Assran, N. Bal-
las, W. Galuba, R. Howes, P.-Y. Huang, S.-W. Li, I. Misra, M. Rabbat,
V. Sharma, G. Synnaeve, H. Xu, H. Jegou, J. Mairal, P. Labatut, A. Joulin,
and P. Bojanowski, “DINOv2: Learning robust visual features without su-
pervision,” Transactions on Machine Learning Research, 2024.

[165] X. Zhai, B. Mustafa, A. Kolesnikov, and L. Beyer, “Sigmoid loss for lan-
guage image pre-training,” in 2023 IEEE/CVF International Conference on
Computer Vision (ICCV), 2023.

[166] Y. Seo, J. Kim, S. James, K. Lee, J. Shin, and P. Abbeel, “Multi-view masked
world models for visual robotic manipulation,” in International Conference
on Machine Learning (ICML), 2023.

[167] T. Tian, B. Li, X. Weng, Y. Chen, E. Schmerling, Y. Wang, B. Ivanovic,
and M. Pavone, “Tokenize the world into object-level knowledge to address
long-tail events in autonomous driving,” in Conference on Robot Learning
(CoRL), 2024.

101

[168] K. C. Lam, F. Pereira, M. Vaziri-Pashkam, K. Woodard, and E. McMahon,
“Mental representations of objects reflect the ways in which we interact with
them,” in Annual Meeting of the Cognitive Science Society, 2020.

[169] J. Jiang, F. Deng, G. Singh, M. Lee, and S. Ahn, “Slot state space models,”

in Advances in Neural Information Processing Systems (NeurIPS), 2024.

[170] C. Kung, S. Lu, Y. Tsai, and Y. Chen, “Action-slot: Visual action-centric
representations for multi-label atomic activity recognition in traffic scenes,”
in IEEE/CVF Conference on Computer Vision and Pattern Recognition
(CVPR), 2024.

[171] B. Liu, Y. Zhu, C. Gao, Y. Feng, Q. Liu, Y. Zhu, and P. Stone, “Libero:
Benchmarking knowledge transfer for lifelong robot learning,” in Advances
in Neural Information Processing Systems (NeurIPS), 2023.

[172] S. James, Z. Ma, D. R. Arrojo, and A. J. Davison, “Rlbench: The robot
learning benchmark & learning environment,” IEEE Robotics and Automa-
tion Letters, vol. 5, no. 2, pp. 3019–3026, 2020.

[173] Y. Zhu, A. Joshi, P. Stone, and Y. Zhu, “Viola: Imitation learning for vision-
based manipulation with object proposal priors,” in Conference on Robot
Learning (CoRL), 2023.

[174] J. Shi, J. Qian, Y. J. Ma, and D. Jayaraman, “Composing pre-trained object-
centric representations for robotics from ”what” and ”where” foundation
models,” in IEEE International Conference on Robotics and Automation
(ICRA), 2024.

[175] K. Mo, L. J. Guibas, M. Mukadam, A. Gupta, and S. Tulsiani, “Where2act:
From pixels to actions for articulated 3d objects,” in IEEE/CVF Interna-
tional Conference on Computer Vision (ICCV), 2021.

[176] Z. Xue and K. Grauman, “Learning fine-grained view-invariant representa-
tions from unpaired ego-exo videos via temporal alignment,” in Advances in
Neural Information Processing Systems (NeurIPS), 2023.

[177] T. Nagarajan and K. Grauman, “Shaping embodied agent behavior with
activity-context priors from egocentric video,” in Advances in Neural Infor-
mation Processing Systems (NeurIPS), 2021.

[178] J. Shi, J. Qian, Y. J. Ma, and D. Jayaraman, “Composing pre-trained object-
centric representations for robotics from ”what” and ”where” foundation

102

models,” in IEEE International Conference on Robotics and Automation
(ICRA), 2024.

[179] R. Peddi, S. Singh, Saurabh, P. Singla, and V. Gogate, “Towards scene graph
anticipation,” in European Conference on Computer Vision (ECCV), 2025.

[180] W. Cai, Y. Ponomarenko, J. Yuan, X. Li, W. Yang, H. Dong, and B. Zhao,
“Spatialbot: Precise spatial understanding with vision language models,”
arXiv preprint arXiv:2406.13642, 2024.

[181] F. Locatello, D. Weissenborn, T. Unterthiner, A. Mahendran, G. Heigold,
J. Uszkoreit, A. Dosovitskiy, and T. Kipf, “Object-centric learning with
slot attention,” in Advances in Neural Information Processing Systems
(NeurIPS), 2020.

[182] C. Zhang, A. Gupta, and A. Zisserman, “Helping hands: An object-aware
ego-centric video recognition model,” in IEEE/CVF International Confer-
ence on Computer Vision (ICCV), 2023.

[183] Z. Wu, N. Dvornik, K. Greff, T. Kipf, and A. Garg, “Slotformer: Unsuper-
vised visual dynamics simulation with object-centric models,” in Interna-
tional Conference on Learning Representations (ICLR), 2023.

[184] Q. Gu, A. Kuwajerwala, S. Morin, K. M. Jatavallabhula, B. Sen, A. Agarwal,
C. Rivera, W. Paul, K. Ellis, R. Chellappa et al., “Conceptgraphs: Open-
vocabulary 3d scene graphs for perception and planning,” in 2024 IEEE
International Conference on Robotics and Automation (ICRA). IEEE, 2024,
pp. 5021–5028.

[185] K. Yamazaki, T. Hanyu, K. Vo, T. Pham, M. Tran, G. Doretto, A. Nguyen,
and N. Le, “Open-fusion: Real-time open-vocabulary 3d mapping and
queryable scene representation,” in 2024 IEEE International Conference on
Robotics and Automation (ICRA).

IEEE, 2024, pp. 9411–9417.

[186] A. K. Sridhar, D. Shah, C. Glossop, and S. Levine, “Nomad: Goal masked
diffusion policies for navigation and exploration,” IEEE International Con-
ference on Robotics and Automation (ICRA), 2023.

[187] B. Li, Y. Wang, J. Mao, B. Ivanovic, S. Veer, K. Leung, and M. Pavone,
“Driving everywhere with large language model policy adaptation,” in
IEEE/CVF Conference on Computer Vision and Pattern Recognition
(CVPR), 2024.

103

[188] H. Shao, Y. Hu, L. Wang, G. Song, S. L. Waslander, Y. Liu, and H. Li,
“Lmdrive: Closed-loop end-to-end driving with large language models,”
in IEEE/CVF Conference on Computer Vision and Pattern Recognition
(CVPR), 2024.

[189] B. Zitkovich, T. Yu, S. Xu et al., “RT-2: vision-language-action models
transfer web knowledge to robotic control,” in 2023 Conference on Robot
Learning (CoRL), 2023.

[190] A. O’Neill, A. Rehman, A. Maddukuri et al., “Open x-embodiment: Robotic
learning datasets and RT-X models : Open x-embodiment collaboration,” in
2024 IEEE International Conference on Robotics and Automation, (ICRA),
2024.

[191] S. Belkhale, T. Ding, T. Xiao, P. Sermanet, Q. Vuong, J. Tompson, Y. Cheb-
otar, D. Dwibedi, and D. Sadigh, “RT-H: action hierarchies using language,”
CoRR, vol. abs/2403.01823, 2024.

[192] Y. Lin, A. Zeng, S. Song, P. Isola, and T. Lin, “Learning to see before
learning to act: Visual pre-training for manipulation,” in IEEE International
Conference on Robotics and Automation (ICRA), 2020.

[193] D. Bolya, C.-Y. Fu, X. Dai, P. Zhang, C. Feichtenhofer, and J. Hoffman, “To-
ken merging: Your vit but faster,” in The Eleventh International Conference
on Learning Representations, 2023.

[194] C. Tran, D. MH Nguyen, M.-D. Nguyen, T. Nguyen, N. Le, P. Xie, D. Son-
ntag, J. Y. Zou, B. Nguyen, and M. Niepert, “Accelerating transformers
with spectrum-preserving token merging,” in Advances in Neural Informa-
tion Processing Systems (NeurIPS), 2025.

[195] Y. Shang, M. Cai, B. Xu, Y. J. Lee, and Y. Yan, “Llava-prumerge: Adap-
tive token reduction for efficient large multimodal models,” arXiv preprint
arXiv:2403.15388, 2024.

[196] W. Li, Y. Yuan, J. Liu, D. Tang, S. Wang, J. Qin, J. Zhu, and L. Zhang,
“Tokenpacker: Efficient visual projector for multimodal llm,” arXiv preprint
arXiv:2407.02392, 2024.

[197] J. Bai, S. Bai, Y. Chu, Z. Cui, K. Dang, X. Deng, Y. Fan, W. Ge, Y. Han,
F. Huang et al., “Qwen technical report,” arXiv preprint arXiv:2309.16609,
2023.

104

[198] W. Hu, Z.-Y. Dou, L. H. Li, A. Kamath, N. Peng, and K.-W. Chang, “Ma-
tryoshka query transformer for large vision-language models,” Neural Infor-
mation Processing Systems (NeurIPS), 2024.

[199] R. Qian, S. Ding, and D. Lin, “Rethinking image-to-video adaptation: An

object-centric perspective,” CoRR, vol. abs/2407.06871, 2024.

[200] K. Vo, T. Phan, K. Yamazaki, M. Tran, and N. Le, “Henasy: Learning to
assemble scene-entities for interpretable egocentric video-language model,”
in Advances in Neural Information Processing Systems (NeurIPS), 2025.

[201] J. Xu, S. De Mello, S. Liu, W. Byeon, T. Breuel, J. Kautz, and
X. Wang, “Groupvit: Semantic segmentation emerges from text supervi-
sion,” in IEEE/CVF Conference on Computer Vision and Pattern Recogni-
tion (CVPR), 2022.

[202] B. Jia, Y. Liu, and S. Huang, “Improving object-centric learning with
query optimization,” in International Conference on Learning Representa-
tions (ICLR), 2023.

[203] K. Cho, B. van Merrienboer, C¸ . G¨ul¸cehre, D. Bahdanau, F. Bougares,
H. Schwenk, and Y. Bengio, “Learning phrase representations using RNN
encoder-decoder for statistical machine translation,” in Conference on Em-
pirical Methods in Natural Language Processing (EMNLP), 2014.

[204] E. J. Hu, Y. Shen, P. Wallis, Z. Allen-Zhu, Y. Li, S. Wang, L. Wang, and
W. Chen, “Lora: Low-rank adaptation of large language models,” in Inter-
national Conference on Learning Representations (ICLR), 2022.

[205] D. Marin, J.-H. R. Chang, A. Ranjan, A. K. Prabhu, M. Raste-
gari, and O. Tuzel, “Token pooling in vision transformers,” ArXiv, vol.
abs/2110.03860, 2021.

[206] H. Touvron, L. Martin, K. Stone, P. Albert et al., “Llama 2: Open foundation

and fine-tuned chat models,” CoRR, vol. abs/2307.09288, 2023.

105