import math
import operator


def write_to_file(dictionary, file):
    sorted_dict = sorted(dictionary.items(), key=operator.itemgetter(1), reverse=True)
    print("Ten most frequent passwords: ")
    for k in sorted_dict[:11]:
        print(k)
    return


filename = "10-million-combos.txt"

stats = {}
count = 1
error_count = 0

print("Starting analysis")
with open(filename, 'r') as input_file:
    for line in input_file:
        try:
            pw = line.split()[1]
            if pw in stats:
                stats[pw] += 1
            else:
                stats[pw] = 1
            if (count % 100000) == 0:
                print(str(count/100000) + '% Done')
        except:
            error_count += 1
        count += 1

print(str(error_count) + ' errors detected')
print(str(len(stats.keys())) + ' distinct passwords found')

write_to_file(stats, "PW_stats.txt")
print(str(count) + ' elements analyzed')

#Author: Spichiger Hannes