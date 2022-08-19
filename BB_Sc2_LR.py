# import des modules d'intérêt
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import math
import random
import matplotlib.pyplot as plt
import csv
from fitter import Fitter

# pip install pandas, sklearn

# groupe contenant les variables système
features_system = ['orientation_1_nb', 'orientation_0_nb', 'orientation_1_duration',
                   'orientation_0_duration', 'orientation_1_duration_mean',
                   'orientation_0_duration_mean', 'isPlugged_1_nb', 'isPlugged_0_nb',
                   'isPlugged_1_duration', 'isPlugged_0_duration', 'isPlugged_1_duration_mean',
                   'isPlugged_0_duration_mean',
                   'isBacklit_1_nb', 'isBacklit_0_nb', 'isBacklit_1_duration',
                   'isBacklit_0_duration', 'isBacklit_1_duration_mean',
                    'isBacklit_0_duration_mean', 'isLocked_1_nb', 'isLocked_0_nb',
                   'isLocked_1_duration', 'isLocked_0_duration',
                   'isLocked_1_duration_mean', 'isLocked_0_duration_mean',
                   'airplaneMode_1_nb', 'airplaneMode_0_nb', 'airplaneMode_1_duration',
                   'airplaneMode_0_duration', 'airplaneMode_1_duration_mean',
                   'airplaneMode_0_duration_mean', 'wifi_event_nb', 'wifi_event_duration',
                   'wifi_event_duration_mean', 'Bluetooth_1_nb', 'Bluetooth_0_nb',
                   'Bluetooth_1_duration', 'Bluetooth_0_duration',
                   'Bluetooth_1_duration_mean', 'Bluetooth_0_duration_mean',
                   'batterySaver_event_nb', 'batterySaver_event_duration',
                   'batterySaver_event_duration_mean', 'audioInput_1_nb',
                   'audioInput_0_nb', 'audioInput_1_duration', 'audioInput_0_duration',
                   'audioInput_1_duration_mean', 'audioInput_0_duration_mean',
                   'audioOutput_1_nb', 'audioOutput_0_nb', 'audioOutput_1_duration',
                   'audioOutput_0_duration', 'audioOutput_1_duration_mean',
                   'audioOutput_0_duration_mean', 'Hidden_nb', 'Receive_nb', 'Dismiss_nb',
                   'Orb_nb', 'IndirectClear_nb', 'DefaultAction_nb', 'lowPowermode_1_nb', 'lowPowermode_0_nb',
                   'lowPowermode_1_duration',
                   'lowPowermode_0_duration', 'lowPowermode_1_duration_mean',
                   'lowPowermode_0_duration_mean', 'batteryPercentage_nb', 'siri_nb',
                   'mediaPlaying_1_nb', 'mediaPlaying_0_nb', 'mediaPlaying_1_duration',
                   'mediaPlaying_0_duration', 'mediaPlaying_1_duration_mean',
                   'mediaPlaying_0_duration_mean', 'appUsage_Session_0',
                   'appUsage_Session_1', 'appUsage_Session_2', 'appUsage_Session_3',
                   'appUsage_Session_4', 'appUsage_Session_5', 'appUsage_Session_6',
                   'appUsage_Session_7', 'appUsage_Session_8', 'appUsage_Session_9',
                   'appUsage_Session_10', 'appUsage_Session_11', 'appUsage_event_nb',
                   'appUsage_event_duration', 'appUsage_event_duration_mean',
                   'Starting_up_nb']


# Returns the id of element within lischte
def get_list_id(lischte, element):
    for i in range(len(lischte)):
        if lischte[i] == element:
            return i

    return -1


# Function calculating the center of gravity of a list of vectors
def cent_of_gravity(vector_list):
    weight = len(vector_list)  # Number of vectors to calculate the center of gravity of. Used for weighting
    dim = len(vector_list[0])  # dimension of the passed vectors
    result = [0.0] * dim  # instantiate a null-vector with dimension dim

    for v in vector_list:
        for i in range(dim):
            result[i] += v[i] / weight

    return result


# Function importing vectors from data file csv. Takes subfolder path from base path as input and returns
# array of vectors
def get_vectors(subpath):
    vectors = []

    with open(Base_path + subpath) as file_name:
        file_read = csv.reader(file_name)
        array = list(file_read)

    index_list = []

    for k in features_system:
        index_list.append(get_list_id(array[0], k))

    for k in array[1:]:
        turn = []
        for j in index_list:
            turn.append(k[j])
        vectors.append(turn)

    #print(vectors)
    return vectors


# Normalises over all vectors in play.
# Accepts as an input a list of a list of vectors. The vectors will be assembled together and normalised.
# Returns a list of a list of normalised vectors grouped and ordered the same way as the input
def normalise(list_o_list):
    input_structure = []
    vector_list = []
    output = []
    for i in list_o_list:
        input_structure.append(len(i))
        vector_list += i
    sc = StandardScaler()
    transformed = sc.fit_transform(X=vector_list).tolist()
    for i in input_structure:
        m = []
        for j in range(i):
            m.append(transformed.pop(0))
        output.append(m)
    return output


# Calculate length of a vector
def vector_len(vector):
    elements_sum = 0
    for i in vector:
        i
        elements_sum += float(i) * float(i)
    return math.sqrt(elements_sum)


# Calculates the vector distance between two vectors
def vector_distance(v1, v2):
    dim = len(v1)
    if dim == len(v2):
        distance_vector = [0.0] * dim
        for i in range(dim):
            distance_vector[i] = v1[i] - v2[i]
        return vector_len(distance_vector)
    else:
        print("Vector dimension is not equal")
        return -1


# Gets the difference from the comparison vector to the center of gravity of the reference
# Takes as an input a list of vectors (reference) and a single vector (comparison)
# Returns the distance as a float
def get_value(reference, comparison):
    cog = cent_of_gravity(reference)
    return vector_distance(cog, comparison)


def get_dist_values_intra(pop, sample_size):
    values_list = []
    for i in range(sample_size):
        vector_selection = random.choices(pop, k=15)
        random.shuffle(vector_selection)
        values_list.append(get_value(vector_selection[:-1], vector_selection[-1]))
    return values_list


# Conducts a PCA on the inputted values (list_o_list) and returns the n_c first coordinates.
def pca_transform(list_o_lists, n_c):
    list_o_lengths = []
    master_list = []
    for i in list_o_lists:
        list_o_lengths.append(len(i))
        master_list += i
    pca = PCA(n_components=n_c)
    temp = list(pca.fit_transform(master_list))
    output = []
    for i in list_o_lengths:
        m = []
        for j in range(i):
            m.append(temp.pop(0))
        output.append(m)
    return output


def get_dist_values_inter(pop1, pop2, sample_size):
    values_list = []
    for i in range(sample_size):
        vector_selection = random.choices(pop1, k=14)
        vector_ref = random.choices(pop2, k=1)
        random.shuffle(vector_selection)
        values_list.append(get_value(vector_selection, vector_ref[0]))
    return values_list

samp = 10000  # Number of samples for the creation of the reference data.
plotting = True
fitting = 0

Base_path = ""  # Path of folder containing anonymized Data


# Recover vectors from csv file
v_Pop1 = get_vectors("/User1_Ref/anonimized_data_user_1_phone_1_2.csv")
v_Pop2 = get_vectors("/User2_Ref/anonimized_data_user_2_phone_2_2.csv")
v_DoI = get_vectors("/Phone1_DoI/anonimized_data_user_1_phone_1_2.csv")  # Vector of values for the day of interest
v_DoI_2 = get_vectors("/Phone2_DoI/anonimized_data_user_1_phone_2_2.csv")

N_Pop1 = len(v_Pop1)  # Number of days in reference population 1
N_Pop2 = len(v_Pop2)  # Number of days in reference population 2

normalised = normalise([v_Pop1, v_Pop2, v_DoI, v_DoI_2])
pcad = pca_transform(normalised, 1)

Pop1_intra = get_dist_values_intra(pcad[0], samp)
Pop1_inter = get_dist_values_inter(pcad[0], pcad[1], samp)
Pop2_intra = get_dist_values_intra(pcad[1], samp)
Pop2_inter = get_dist_values_inter(pcad[1], pcad[0], samp)
dist_DoI_Pop1 = get_value(pcad[0], pcad[2][0])
dist_DoI_Pop2 = get_value(pcad[1], pcad[2][0])

dist_DoI2_Pop1 = get_value(pcad[0], pcad[3][0])
dist_DoI2_Pop2 = get_value(pcad[1], pcad[3][0])

print(dist_DoI_Pop1)
print(dist_DoI_Pop2)
print(dist_DoI2_Pop1)
print(dist_DoI2_Pop2)


if fitting:
    f1 = Fitter(Pop1_intra, distributions='beta')
    f1.fit()
    print("Pop 1")
    print(f1.summary())
    print(f1.get_best())

    f2 = Fitter(Pop2_intra, distributions='expon')
    f2.fit()
    print("Pop 2")
    print(f2.summary())
    print(f2.get_best())

# titre
if plotting:
    plt.title("Distance from center Pop 1")
    plt.subplot(211)
    plt.hist(Pop1_intra, fc=(0, 0, 0, 0.2), edgecolor='black', bins=np.arange(0, 15, 0.25), density=True, stacked=True, label="P1 intra")
    if fitting:
        f1.plot_pdf()
    plt.hist(Pop1_inter, fc=(0, 0, 0, 0.5), edgecolor='black', bins=np.arange(0, 15, 0.25), density=True, stacked=True, label="P1 inter")
    #point du premier utilisateur (appartenant au groupe)
    #b = plt.axvline(new_v_y,color='g',linestyle='dashed', label="Groupe")
    # # point du deuxième utilisateur (n'appartenant pas au groupe)
    #c = plt.axvline(new_v_z,color='r',linestyle='dashed', label="Autre")
    # #ajout des légendes
    #plt.legend(handles=[b,c],bbox_to_anchor=(0.8,0.95))
    #axes nommés
    plt.plot(2 * [dist_DoI_Pop1], [0.00, 0.5], color='black', label="E_S1")
    plt.plot(2 * [dist_DoI2_Pop1], [0.00, 0.5], color='black', linestyle='dashed', label="E_S2")

    plt.legend()

    plt.ylabel("Occurrence")

    plt.subplot(212)
    plt.hist(Pop2_intra, fc=(0, 0, 0, 0.5), edgecolor='black', bins=np.arange(0, 15, 0.25), density=True, stacked=True, label="P2 intra")
    plt.hist(Pop2_inter, fc=(0, 0, 0, 0.2), edgecolor='black', bins=np.arange(0, 15, 0.25), density=True, stacked=True, label="P2 inter")
    if fitting:
        f2.plot_pdf()
    plt.plot(2 * [dist_DoI_Pop2], [0.00, 1.5], color='black', label="E_S1")
    plt.plot(2 * [dist_DoI2_Pop2], [0.00, 1.5], color='black', linestyle='dashed', label="E_S2")
    plt.xlabel("Distance")
    plt.ylabel("Occurrence")
    plt.legend()


    plt.show()



# Auteur : Spichiger Hannes
# Adapted from Michelet Gaëtan
