# Thesis

This repository contains all scripts used in the projects related to my doctorate thesis in Forensic Science entitled 
The Evaluation of Mobile Device Evidence under Person-Level, Location-Focused Propositions

This thesis is currently being finished and handed in to the committee. As soon as it is in it's final form, the pdf will be referenced here for context as well. 

This repository is of purely archivary nature. The scripts are not maintained and will not be updated.
Research projects based on scripts in this repository will be placed in a dedicated repository.

The scripts do the following:

- BB_anonymize.py is a script lightly adapted from Michelet (2021) used to recover system-characteristics used for behavioural biometrics from knowledgeC.db and lockdown.log. This script was used in Chapters 5 and 7 of the thesis.
- BB_Sc2_Analysis is a rough script used to conduct some general analysis of the results obtained. This script was used in an exploratory way to test options in chapter 5.
- BB_Sc2_LR.py generates an LR for observed behavioural biometric characteristics as described in Chapter 5.
- BB_Sc4_Analysis.py is a rough script used to conduct some general analysis of the results obtained. This script was used in an exploratory way to test options in chapter 7.
- BB_Sc4_LR generates an LR for observed behavioural biometric characteristics as described in Chapter 7.
- BN_Hugin.zip is a zip folder containing all the Bayes Nets as Hugin models used in the Thesis.
- GPS_LR.py generates an LR for a GPS trace as done in Chapters 6 and 7 of the thesis.
- PW_stats.py analyses the 10 million Passwords-dump (Burnett, 2015) and creates statistics for it.
- PW_LR_getStats.py allows to interrogate the statistics generated by PW_stats.py to obtain password frequencies used in Chapter 7.
- R_Scripts_Sim.zip contains all R-Scripts used for the simulation of the Bayes Net's behaviour.




## References

Burnett, M., 2015. *Today I Am Releasing Ten Million Passwords* [WWW Document]. Medium. URL https://xato.net/today-i-am-releasing-ten-million-passwords-b6278bbe7495 (accessed 7.4.22).


Michelet, G., 2021. *D??tecter un changement d???utilisateur sur un smartphone* (Master Thesis). University of Lausanne, Lausanne.

