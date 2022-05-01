import csv
import pickle


# part of speech
POS_KEY = {'noun': 'n', 'verb': 'v', 'adj': 'a', 'adv': 'r'}

POINTER_TYPES_TO_IGNORE = {';u', '-u', '<', '<x'}  # usage domains/members, adjective/verb derivations
IGNORE_ANTONYMS = True
POINTER_SEQUENCES_TO_IGNORE = {  # Pointer type ignored if it is a value preceded by key.
    ';c': '-c', '-c': ';c', ';r': '-r', '-r': ';r', ';u': '-u', '-u': ';u',
}

POINTER_SYMBOL_KEY = {
    '^': {'name': 'also see', 'phrase': 'which is related to'},  # non-reflexive
    '__start': {'name': 'start', 'phrase': '(start marker)'},  # custom pointer type
    '__end': {'name': 'end', 'phrase': '(end marker)'},  # custom pointer type
    '?p': {'name': 'word pivot', 'phrase': 'which is the same word as'},  # custom pointer type  # self-reflexive
    '!': {'name': 'antonym', 'phrase': 'which is the opposite of'},  # self-reflexive
    '&': {'name': 'similar to', 'phrase': 'which is similar to'},  # self-reflexive
    '$': {'name': 'verb group', 'phrase': 'which is a related verb to'},  # self-reflexive
    '=': {'name': 'attribute', 'phrase': 'which is a value or attribute of'},  # self-reflexive
    '+': {'name': 'derivationally related form', 'phrase': 'which has the same root form as'},  # self-reflexive
    # Remaining pointers are ordered with reflexive pointers paired together.
    '@': {'name': 'hypernym', 'phrase': 'which is a kind of'},
    '~': {'name': 'hyponym', 'phrase': 'a kind of which is'},
    '@i': {'name': 'instance hypernym', 'phrase': 'which is an instance of'},
    '~i': {'name': 'instance hyponym', 'phrase': 'an instance of which is'},
    '#m': {'name': 'member holonym', 'phrase': 'which is a member of'},
    '%m': {'name': 'member meronym', 'phrase': 'a member of which is'},
    '#s': {'name': 'substance holonym', 'phrase': 'which is a substance of'},
    '%s': {'name': 'substance meronym', 'phrase': 'a substance of which is'},
    '#p': {'name': 'part holonym', 'phrase': 'which is a part of'},
    '%p': {'name': 'part meronym', 'phrase': 'a part of which is'},
    ';c': {'name': 'domain of synset - topic', 'phrase': 'which is associated with the category'},
    '-c': {'name': 'member of this domain - topic', 'phrase': 'which is a category sometimes associated with'},
    ';r': {'name': 'domain of synset - region', 'phrase': 'which is associated with the region'},
    '-r': {'name': 'member of this domain - region', 'phrase': 'which is a region sometimes associated with'},
    ';u': {'name': 'domain of synset - usage', 'phrase': 'which is associated with the usage'},
    '-u': {'name': 'member of this domain - usage', 'phrase': 'which is a usage sometimes associated with'},
    '<': {'name': 'participle of verb', 'phrase': 'which is an adjective derived from the verb'},
    '<x': {'name': 'participle of verb reflex', 'phrase': 'which is the root verb for the adjective'},
    # custom reflex pointer (above)
    '\\': {'name': 'pertainym', 'phrase': 'which is of or pertaining to'},
    '\\x': {'name': 'pertainym reflex', 'phrase': 'which is the basis for'},  # custom reflex pointer
    '*': {'name': 'entailment', 'phrase': 'which cannot be done without'},
    '*x': {'name': 'entailment reflex', 'phrase': 'which is always done with'},  # custom reflex pointer
    '>': {'name': 'cause', 'phrase': 'which is caused by'},
    '>x': {'name': 'cause reflex', 'phrase': 'which can cause'},  # custom reflex pointer
}


def parse_index_files():
    """Creates a dictionary from WordNet index.pos files with words/collocations as the keys.
Each key-value is a list of synset ids connected to the word/collocation in the key."""

    index_dict = {}

    for pos in POS_KEY:

        path = 'wordnet-db/index.' + pos
        with open(path, newline='') as file:
            file_lines = list(csv.reader(file, delimiter=' '))

        for line_data_as_list in file_lines:

            word = line_data_as_list[0]

            if word == '':
                continue

            if word not in index_dict:
                index_dict[word] = []

            num_synsets = int(line_data_as_list[2])
            num_diff_pointers = int(line_data_as_list[3])
            for synset_index in range(num_synsets):
                synset_num = line_data_as_list[6 + num_diff_pointers + synset_index]
                synset_id = POS_KEY[pos] + synset_num
                index_dict[word].append(synset_id)

    print('Parsed WordNet index files.')
    return index_dict


def parse_data_files():
    """Creates a dictionary from WordNet data.pos files with the synset ids as the keys."""

    data_dict = {}

    for pos in POS_KEY:

        path = 'wordnet-db/data.' + pos
        with open(path, newline='') as file:
            file_lines = list(csv.reader(file, delimiter='|'))

        for line in file_lines:

            if line[0][:2] == '  ':
                continue

            line_data_as_list = line[0][:-1].split(' ')

            num_words = int(line_data_as_list[3], 16)  # Convert from hexadecimal.
            words = []
            for word_num in range(num_words):
                word = line_data_as_list[4 + word_num * 2]
                words.append(word)

            synset_id = f'{POS_KEY[pos]}{line_data_as_list[0]}'
            if synset_id not in data_dict:
                data_dict[synset_id] = {'out': [], 'in': []}

            data_dict[synset_id]['words'] = tuple(words)
            data_dict[synset_id]['pos'] = pos
            data_dict[synset_id]['gloss'] = line[1][1:-2]

            num_pointers = int(line_data_as_list[4 + num_words * 2])
            for pointer_num in range(num_pointers):
                pointer_elems = []
                for pointer_elem_num in range(4):
                    pointer_elem = line_data_as_list[5 + num_words * 2 + pointer_num * 4 + pointer_elem_num]
                    pointer_elems.append(pointer_elem)
                pointer_words_hex = pointer_elems[3]
                pointer_source_word_index = int(pointer_words_hex[:2], 16) - 1
                pointer_target_word_index = int(pointer_words_hex[2:], 16) - 1
                pointer_pos = pointer_elems[2]
                if pointer_pos == 's':
                    pointer_pos = 'a'  # Merge 'satellite adjectives' into 'adjectives'.
                pointer_id = f'{pointer_pos}{pointer_elems[1]}'
                if pointer_id not in data_dict:
                    data_dict[pointer_id] = {'out': [], 'in': []}
                pointer_out = [pointer_elems[0], pointer_id, pointer_source_word_index, pointer_target_word_index]
                pointer_in = [pointer_elems[0], synset_id, pointer_source_word_index, pointer_target_word_index]
                if pointer_elems[0] == '!':  # Always place antonym first in pointers list.
                    data_dict[synset_id]['out'].insert(0, pointer_out)
                    data_dict[pointer_id]['in'].insert(0, pointer_in)
                else:
                    data_dict[synset_id]['out'].append(pointer_out)
                    data_dict[pointer_id]['in'].append(pointer_in)

    print('Parsed WordNet data files.')
    return data_dict


def synset_ids_to_integers(wordnet_data, wordnet_index):

    new_wordnet_data = []
    new_wordnet_index = {}
    id_change_key = {}

    synset_index = 0
    for synset_id in wordnet_data:
        new_wordnet_data.append(wordnet_data[synset_id])
        id_change_key[synset_id] = synset_index
        synset_index += 1

    for synset in new_wordnet_data:
        for direction in ['out', 'in']:
            for pointer in synset[direction]:
                pointer[1] = id_change_key[pointer[1]]

    for word in wordnet_index:
        synset_id_list = wordnet_index[word]
        new_synset_id_list = []
        for synset_id in synset_id_list:
            changed_synset_id = id_change_key[synset_id]
            new_synset_id_list.append(changed_synset_id)
        new_wordnet_index[word] = tuple(new_synset_id_list)

    print('Changed synset_ids to consecutive integers.')
    return [new_wordnet_data, new_wordnet_index]


def add_word_pivots(wordnet_data, wordnet_index):
    for word in wordnet_index:
        synset_list = wordnet_index[word]
        if len(synset_list) < 2:
            continue
        for synset_id in synset_list:
            source_words = []
            for original_word in wordnet_data[synset_id]['words']:
                syntax_marker_removed = original_word.split('(', 1)[0]
                lower_case = syntax_marker_removed.lower()
                source_words.append(lower_case)
            source_word_num = source_words.index(word)
            synset_list_minus_self = list(synset_list)
            synset_list_minus_self.remove(synset_id)
            existing_out_pointers = [pointer[1] for pointer in wordnet_data[synset_id]['out']]
            existing_in_pointers = [pointer[1] for pointer in wordnet_data[synset_id]['in']]
            for pointer_id in synset_list_minus_self:
                target_words = []
                for original_word in wordnet_data[pointer_id]['words']:
                    syntax_marker_removed = original_word.split('(', 1)[0]
                    lower_case = syntax_marker_removed.lower()
                    target_words.append(lower_case)
                target_word_num = target_words.index(word)
                if pointer_id not in existing_out_pointers:
                    out_pointer = ['?p', pointer_id, source_word_num, target_word_num]
                    wordnet_data[synset_id]['out'].append(out_pointer)
                if pointer_id not in existing_in_pointers:
                    in_pointer = ['?p', pointer_id, target_word_num, source_word_num]
                    wordnet_data[synset_id]['in'].append(in_pointer)
    print('Added word pivots.')
    return wordnet_data


def add_missing_pointers(wordnet_data):

    pointer_reflexes = {
        '?p': '?p', '!': '!', '&': '&', '$': '$', '=': '=', '+': '+',
        '@': '~', '~': '@', '@i': '~i', '~i': '@i',
        '#m': '%m', '%m': '#m', '#s': '%s', '%s': '#s', '#p': '%p', '%p': '#p',
        ';c': '-c', '-c': ';c', ';r': '-r', '-r': ';r', ';u': '-u', '-u': ';u',
        '<': '<x', '<x': '<', '\\': '\\x', '\\x': '\\', '*': '*x', '*x': '*', '>': '>x', '>x': '>',
    }

    missing_reflex_pointer_count = {}

    for synset_id in range(len(wordnet_data)):
        for direction in ['out', 'in']:
            for pointer in wordnet_data[synset_id][direction]:

                pointer_type = pointer[0]
                pointer_id = pointer[1]
                found_reflex = False

                if pointer_type in pointer_reflexes:
                    # Pointers which may point back to synset_id.
                    pointers_of_pointer = wordnet_data[pointer_id][direction]
                    for possible_reflex_pointer in pointers_of_pointer:
                        # if possible_reflex_pointer[1] == synset_id \
                        #         and possible_reflex_pointer[0] == pointer_reflexes[pointer_type]:
                        #     # Check for reflex of specific type.
                        if possible_reflex_pointer[1] == synset_id:  # If reflexive.
                            if possible_reflex_pointer[0] not in POINTER_TYPES_TO_IGNORE:  # If not type to ignore.
                                if not (possible_reflex_pointer[0] == '!' and IGNORE_ANTONYMS):
                                    # If not ignorable antonym.
                                    found_reflex = True
                                    break

                if not found_reflex:
                    if pointer_type in pointer_reflexes:

                        new_pointer_type = pointer_reflexes[pointer_type]
                        new_pointer = [new_pointer_type, synset_id, pointer[3], pointer[2]]  # Swapped pointer words.
                        wordnet_data[pointer_id][direction].append(new_pointer)

                        # # Print out explanation for added pointer.
                        # direction_num = {'out': 0, 'in': 1}[direction]
                        # explanation = f'"{wordnet_data[pointer_id]["words"][new_pointer[2][direction_num]]}" ' \
                        #               f'{POINTER_SYMBOL_KEY[new_pointer[0]]["phrase"]} ' \
                        #               f'"{wordnet_data[synset_id]["words"][new_pointer[2][direction_num * -1 + 1]]}"'
                        # print(f'MISSING POINTER ADDED at synset id {pointer_id}: {new_pointer} | {explanation}')

                    elif pointer_type in missing_reflex_pointer_count:
                        missing_reflex_pointer_count[pointer_type] += 1
                    else:
                        missing_reflex_pointer_count[pointer_type] = 1

    print('Added missing pointers.')
    print('Pointers with no reflex not added:', missing_reflex_pointer_count)

    # Do check that all 'out' pointers should have a correspoinding 'in' pointer and vice versa.
    for synset_id in range(len(wordnet_data)):
        for direction in ['out', 'in']:
            opposite_direction = {'out': 'in', 'in': 'out'}[direction]
            for pointer in wordnet_data[synset_id][direction]:
                pointer_id = pointer[1]
                mirror_pointers = wordnet_data[pointer_id][opposite_direction]
                found_mirror = False
                for possible_mirror_pointer in mirror_pointers:
                    if possible_mirror_pointer[1] == synset_id:
                        found_mirror = True
                        break
                if not found_mirror:
                    raise Exception(f'wordnet_data["{synset_id}"]["{direction}"] contains the pointer {pointer}.'
                                    f'Could not find a corresponding pointer in '
                                    f'wordnet_data["{pointer_id}"]["{opposite_direction}"].')

    return wordnet_data


def calculate_groups(wordnet_data):

    group_merge_key = {}

    group_id = -1

    for synset in wordnet_data:
        synset['group'] = 'x'

    for synset_id in range(len(wordnet_data)):

        if wordnet_data[synset_id]['group'] != 'x':
            continue

        group_merge_key[group_id] = group_id
        wordnet_data[synset_id]['group'] = group_id
        no_group = True

        out_pointer_ids = []
        for out_pointer in wordnet_data[synset_id]['out']:
            if out_pointer[0] in POINTER_TYPES_TO_IGNORE:
                continue
            if IGNORE_ANTONYMS and out_pointer[0] == '!':
                continue
            out_pointer_id = out_pointer[1]
            out_pointer_ids.append(out_pointer_id)

        for in_pointer in wordnet_data[synset_id]['in']:

            if in_pointer[0] in POINTER_TYPES_TO_IGNORE:
                continue
            if IGNORE_ANTONYMS and in_pointer[0] == '!':
                continue

            in_pointer_id = in_pointer[1]

            if in_pointer_id in out_pointer_ids:
                no_group = False
                pointer_group_id = wordnet_data[in_pointer_id]['group']
                if pointer_group_id == 'x':
                    wordnet_data[in_pointer_id]['group'] = group_id
                else:
                    if abs(group_merge_key[group_id]) > abs(group_merge_key[pointer_group_id]):
                        group_merge_key[group_id] = group_merge_key[pointer_group_id]
                    else:
                        group_merge_key[pointer_group_id] = group_merge_key[group_id]

        if no_group:
            del group_merge_key[group_id]
            group_merge_key[synset_id] = synset_id
            wordnet_data[synset_id]['group'] = synset_id
        else:
            group_id += -1

    for group_id in group_merge_key:
        group_ids = [group_id]
        while True:
            merge_group_id = group_merge_key[group_ids[-1]]
            group_ids.append(merge_group_id)
            if group_merge_key[merge_group_id] == merge_group_id:
                break
        for intermediate_group_id in group_ids[:-1]:
            group_merge_key[intermediate_group_id] = group_ids[-1]

    base_group_id_key = {}
    base_group_id_sequence = -1
    for group_id in group_merge_key:
        if group_merge_key[group_id] == group_id:
            if group_id < 0:
                base_group_id_key[group_id] = base_group_id_sequence
                base_group_id_sequence += -1
            else:
                base_group_id_key[group_id] = group_id

    for synset in wordnet_data:
        current_group_id = synset['group']
        merge_group_id = group_merge_key[current_group_id]
        base_group_id = base_group_id_key[merge_group_id]
        synset['group'] = base_group_id

    print('Added group_ids.')
    return wordnet_data


def create_group_map(wordnet_data):

    # INITIALIZE GROUP MAP

    group_map = {}
    for synset in wordnet_data:

        group_id = synset[0]
        if group_id not in group_map:
            group_map[group_id] = [set(), set()]  # First list is direct connections; second is distant connections.

        for pointer in synset[4]:

            pointer_type = pointer[0]
            pointer_id = pointer[1]
            pointer_group_id = wordnet_data[pointer_id][0]

            if pointer_group_id == group_id or pointer_type in POINTER_TYPES_TO_IGNORE:
                continue
            if IGNORE_ANTONYMS and pointer_type == '!':
                continue

            group_map[group_id][0].add(pointer_group_id)

    # ADD CONNECTIONS AT ALL DEPTHS

    for group_id in group_map:
        vanguard = group_map[group_id][0]
        while True:
            new_vanguard = []
            for vanguard_group_id in vanguard:
                for pointer in group_map[vanguard_group_id][0]:
                    if pointer not in group_map[group_id][0] and pointer not in group_map[group_id][1]:
                        group_map[group_id][1].add(pointer)
                        new_vanguard.append(pointer)
            if len(new_vanguard) != 0:
                vanguard = new_vanguard
            else:
                break

    return group_map


def group_map_to_tuples(group_map):
    tuple_group_map = {}
    for group_id in group_map:
        adjacent_groups = group_map[group_id][0]
        distant_groups = group_map[group_id][1]
        tuple_group_map[group_id] = (adjacent_groups, distant_groups)
    return tuple_group_map


def find_groups_without_opposites(wordnet_data, group_map):

    antonym_in_group = {}  # Each key-value is a boolean for if group has an antonym.
    for synset in wordnet_data:
        group_num = synset[0]
        if group_num not in antonym_in_group:
            antonym_in_group[group_num] = False
        if len(synset[4]) > 0:
            if synset[4][0][0] == '!':
                antonym_in_group[group_num] = True

    antonym_reachable_from_group = {}  # Each key-value is a boolean for if group can reach an antonym.
    for group_num in antonym_in_group:
        if not antonym_in_group[group_num]:
            if group_num not in antonym_reachable_from_group:
                antonym_reachable_from_group[group_num] = False
        else:
            antonym_reachable_from_group[group_num] = True
            continue
        if not antonym_reachable_from_group[group_num]:
            for adjacent_group in group_map[group_num][0]:
                if antonym_in_group[adjacent_group]:
                    antonym_reachable_from_group[group_num] = True
                    break
        if not antonym_reachable_from_group[group_num]:
            for distant_group in group_map[group_num][1]:
                if antonym_in_group[distant_group]:
                    antonym_reachable_from_group[group_num] = True
                    break

    groups_without_opposites = set()
    for group_num in antonym_reachable_from_group:
        if not antonym_reachable_from_group[group_num]:
            groups_without_opposites.add(group_num)

    with open("groups-without-opposites.pkl", "wb") as file:
        pickle.dump(tuple(groups_without_opposites), file)


def pointers_to_tuples(data_db):
    for synset in data_db:
        for direction in ('out', 'in'):
            pointer_tuples = []
            for pointer in synset[direction]:
                pointer_tuples.append(tuple(pointer))
            synset[direction] = tuple(pointer_tuples)
    return data_db


def synset_dict_to_tuple(data_db):
    new_data_db = []
    for synset in data_db:
        synset_tuple = (synset['group'], synset['pos'], synset['gloss'], synset['words'], synset['out'], synset['in'])
        new_data_db.append(synset_tuple)
    print('Converted dictionary to tuples.')
    return tuple(new_data_db)


def write_data_files(data_db, num_synsets_each_file=200000):

    file_num = 0
    need_another_file = True

    while need_another_file:
        start_index = file_num * num_synsets_each_file
        end_index = start_index + num_synsets_each_file
        if end_index > len(data_db):
            end_index = len(data_db)
            need_another_file = False
        data_db_slice = data_db[start_index:end_index]
        with open(f"wordnet-data-{file_num}.pkl", "wb") as file:
            pickle.dump(data_db_slice, file)
        file_num += 1


def prepare_database():

    print('Started prepare_database().')

    index_db = parse_index_files()
    data_db = parse_data_files()

    data_index_new_ids = synset_ids_to_integers(data_db, index_db)  # Index converted from lists to tuples here.
    data_db_new_ids = data_index_new_ids[0]
    index_db_new_ids = data_index_new_ids[1]

    data_db_plus_word_pivots = add_word_pivots(data_db_new_ids, index_db_new_ids)
    data_db_plus_missing_pointers = add_missing_pointers(data_db_plus_word_pivots)
    data_db_plus_groups = calculate_groups(data_db_plus_missing_pointers)
    data_db_all_tuples = tuple(pointers_to_tuples(data_db_plus_groups))
    data_db_no_dict = synset_dict_to_tuple(data_db_all_tuples)

    with open('wordnet-index.pkl', 'wb') as file:
        pickle.dump(index_db_new_ids, file)
    print('Created wordnet-index.pkl')

    write_data_files(data_db_no_dict)
    print('Created wordnet-data-X.pkl')

    group_map = create_group_map(data_db_no_dict)
    group_map_all_tuples = group_map_to_tuples(group_map)
    with open("group-map.pkl", "wb") as file:
        pickle.dump(group_map_all_tuples, file)
    print('Created group-map.pkl')

    find_groups_without_opposites(data_db_no_dict, group_map_all_tuples)
    print('Created groups-without-opposites.pkl')

    print('Completed prepare_database().')


# prepare_database()
