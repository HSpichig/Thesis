

password = input('Enter password you would like the number of occurrences of: ')

num_of_elements = 9997987
num_of_occurrences = 0

print("Searching...")

with open('PW_stats.txt', 'r') as f:
    for line in f:
        pw_stat = line.split('\t')
        if pw_stat[0] == password:
            num_of_occurrences = float(pw_stat[1])
            print('Password found')
            break

if num_of_occurrences == 0:
    print('Password not found')

frequency = num_of_occurrences / num_of_elements

LR = 1 / (frequency * 6.5)

print("Found " + str(int(num_of_occurrences)) + " found in " + str(num_of_elements) + " elements")
print("Frequency: " + str(frequency))
print("LR: " + str(LR))

#Author: Spichiger Hannes