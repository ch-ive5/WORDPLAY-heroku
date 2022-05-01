import random
import manage_database
from copy import deepcopy


START_HUE = 280
HUE_STEP = -18

POINTER_SYMBOL_KEY = manage_database.POINTER_SYMBOL_KEY
POINTER_TYPES_TO_IGNORE = manage_database.POINTER_TYPES_TO_IGNORE
IGNORE_ANTONYMS = manage_database.IGNORE_ANTONYMS
POINTER_SEQUENCES_TO_IGNORE = manage_database.POINTER_SEQUENCES_TO_IGNORE


def remove_non_wordnet_chars(string):
    wordnet_chars = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd',
                     'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r',
                     's', 't', 'u', 'v', 'w', 'x', 'y', 'z', ' ', '-', "'", '.', '/'}
    wordnet_chars_only = []
    for char in string:
        if char.lower() in wordnet_chars:
            wordnet_chars_only.append(char)
    return ''.join(wordnet_chars_only)


def clean_string(string):

    # Convert all letters to lower-case.
    lowercase_string = string.lower()

    wordnet_chars_only = remove_non_wordnet_chars(lowercase_string)

    # Remove superfluous spaces.
    extra_spaces_removed = []
    last_char_space = True
    for char in wordnet_chars_only:
        if char == ' ':
            if last_char_space:
                continue
            last_char_space = True
        else:
            last_char_space = False
        extra_spaces_removed.append(char)
    if len(extra_spaces_removed) > 0:
        if extra_spaces_removed[-1] == ' ':
            extra_spaces_removed.pop(-1)
    extra_spaces_removed_string = ''.join(extra_spaces_removed)

    # Convert spaces to underscores.
    cleaned_string = extra_spaces_removed_string.replace(' ', '_')

    return cleaned_string


def random_main_group_word(wordnet_data):
    while True:
        rand_synset_id = random.randint(0, len(wordnet_data))
        if wordnet_data[rand_synset_id][0] == -1:
            word = random.choice(wordnet_data[rand_synset_id][3])
            formatted_word = word.replace('_', ' ').split('(')[0]
            return formatted_word


def get_tree(wordnet_data, wordnet_index, group_map, start_word, target_word):
    """Returns a "tree", or a list of recursively nested lists encoding various paths from start to end synsets.

Start_word and target_word should be lower case, and spaces should be replaced with underscores.

Returns dictionary with keys "status" and "data". Status can be "ok" or "error".
If status is ok, data is path_memory tree. If status is error, data is a string describing the error.

TREE DATA STRUCTURE: tree[direction][generation][sibling_group_index][sibling_index]
    DIRECTION: 0 for direction branching from start, 1 for direction branching from end.
    GENERATION: 0 is the first/oldest generation where branching begins at start and end synsets.
    -1 is last/newest generation where connecting synsets are found in common for both directions.
    SIBLING GROUP INDEX: Index of sibling group, containing pointers from the same parent synset in previous generation.
    SIBLING_INDEX: Index of pointer within sibling group."""

    def prune_tree(directions_to_prune, synset_connectors):
        """Removes pointers not part of synset_connectors paths, empty pointer child groups,
and parent pointers with no children from path_memory.
Directions_to_prune is list (valid directions are integers 0 and 1).
Synset_connectors is list of synset_ids to keep in last generation.
Pass in empty list to synset_connectors if no connection found yet."""

        # If connection found this iteration, delete any non-connecting pointers from last generation.
        if len(synset_connectors) > 0:
            for both_directions in range(2):
                for sibling_group_index in range(len(path_memory[both_directions][-1])):
                    sibling_indices_to_delete = []
                    for sibling_index in range(len(path_memory[both_directions][-1][sibling_group_index])):
                        if path_memory[both_directions][-1][sibling_group_index][sibling_index][1] \
                                not in synset_connectors:
                            # Add non-connecting synsets to delete queue.
                            sibling_indices_to_delete.insert(0, sibling_index)
                    for sibling_index in sibling_indices_to_delete:
                        # Delete synsets in queue.
                        del path_memory[both_directions][-1][sibling_group_index][sibling_index]

        for direction_to_prune in directions_to_prune:

            # Prune empty sibling groups and parents of empty sibling groups.
            for generation in range(len(path_memory[direction_to_prune]) - 1):

                # Initialize delete queues.
                empty_sibling_groups = []  # List of sibling group indices to delete in current generation.
                parents_without_children = []  # List of parent coordinates to delete in previous generation.
                # Each coordinate is encoded as a list: [parent_group_index, parent_index_within_group]

                # Add empty sibling groups and parents without children to delete queues.
                for sibling_group_index in range(len(path_memory[direction_to_prune][-1 - generation])):
                    if len(path_memory[direction_to_prune][-1 - generation][sibling_group_index]) == 0:
                        # Run if sibling group is empty.
                        empty_sibling_groups.insert(0, sibling_group_index)  # Add sibling group to delete queue.
                        sibling_group_coords = [direction_to_prune, -1 - generation, sibling_group_index]
                        parent_coords = get_parent_coords(sibling_group_coords, path_memory)[2:]
                        parents_without_children.insert(0, parent_coords)

                # Delete empty sibling groups and parents without children listed in delete queues.
                for sibling_group_index in empty_sibling_groups:
                    del path_memory[direction_to_prune][-1 - generation][sibling_group_index]
                for parent_coords in parents_without_children:
                    parent_group_index = parent_coords[0]
                    parent_index_within_group = parent_coords[1]
                    del path_memory[direction_to_prune][-2 - generation][parent_group_index][parent_index_within_group]

    # Check which start synsets connect with which end synsets, if any.
    start_synset_ids = wordnet_index[start_word]
    target_synset_ids = wordnet_index[target_word]
    pruned_start_synset_ids = set()
    pruned_target_synset_ids = set()
    for start_synset_id in start_synset_ids:
        for target_synset_id in target_synset_ids:
            target_group = wordnet_data[target_synset_id][0]
            start_group = wordnet_data[start_synset_id][0]
            adjacent_groups = group_map[start_group][0]
            distant_groups = group_map[start_group][1]
            if target_group == start_group or target_group in adjacent_groups or target_group in distant_groups:
                pruned_start_synset_ids.add(start_synset_id)
                pruned_target_synset_ids.add(target_synset_id)
    if len(pruned_start_synset_ids) == 0 or len(pruned_target_synset_ids) == 0:
        return {'status': 'error', 'data': 'No connection found.'}

    start_pointers_list = []
    end_pointers_list = []
    search_directions = [0, 1]

    for synset_id in pruned_start_synset_ids:
        lower_case_words = [word.lower().split('(')[0] for word in wordnet_data[synset_id][3]]
        word_index = lower_case_words.index(start_word)
        child_pointer = ('__start', synset_id, word_index, word_index)
        start_pointers_list.append(child_pointer)

    for synset_id in pruned_target_synset_ids:
        lower_case_words = [word.lower().split('(')[0] for word in wordnet_data[synset_id][3]]
        word_index = lower_case_words.index(target_word)
        child_pointer = ('__end', synset_id, word_index, word_index)
        end_pointers_list.append(child_pointer)

    path_memory = [[[start_pointers_list]], [[end_pointers_list]]]
    visited_synsets = [pruned_start_synset_ids, pruned_target_synset_ids]
    found_connection = False
    connecting_synsets = set()

    for parent_synset_id in pruned_start_synset_ids:
        if parent_synset_id in pruned_target_synset_ids:
            found_connection = True
            connecting_synsets.add(parent_synset_id)
    if found_connection:
        prune_tree([0, 1], connecting_synsets)
        return {
            'status': 'ok',
            'data': path_memory,
            'synsets_visited': len(visited_synsets[0]) + len(visited_synsets[1])
        }

    while True:  # Each loop is one layer in a breadth-first search.

        for direction in search_directions:

            next_generation = []

            for parent_group in path_memory[direction][-1]:  # Getting pointer groupings from previous generation.
                for parent_pointer in parent_group:  # Find neighbor_synsets of synsets_currently_visiting.

                    sibling_group = []

                    parent_synset_id = parent_pointer[1]
                    for child_pointer in wordnet_data[parent_synset_id][direction + 4]:

                        child_pointer_symbol = child_pointer[0]
                        if child_pointer_symbol in POINTER_TYPES_TO_IGNORE:
                            continue  # Ignore specified pointer types.
                        if IGNORE_ANTONYMS and child_pointer_symbol == '!':
                            continue  # Ignore antonyms.
                        if parent_pointer[0] in POINTER_SEQUENCES_TO_IGNORE:
                            if POINTER_SEQUENCES_TO_IGNORE[parent_pointer[0]] == child_pointer_symbol:
                                continue  # Ignore specified pointer type sequences.

                        child_pointer_id = child_pointer[1]

                        if child_pointer_id in visited_synsets[direction * -1 + 1]:
                            found_connection = True
                            connecting_synsets.add(child_pointer_id)

                        # Add pointer only if it refers to a synset not already marked to skip.
                        if child_pointer_id not in visited_synsets[direction]:
                            visited_synsets[direction].add(child_pointer_id)
                            sibling_group.append(child_pointer)

                    next_generation.append(sibling_group)

            path_memory[direction].append(next_generation)

            prune_directions = [direction]
            if found_connection:
                prune_directions = [0, 1]
            prune_tree(prune_directions, connecting_synsets)

            if found_connection:
                return {
                    'status': 'ok',
                    'data': path_memory,
                    'synsets_visited': len(visited_synsets[0]) + len(visited_synsets[1])
                }

            empty_generation = True
            for sibling_group in next_generation:
                if len(sibling_group) > 0:
                    empty_generation = False
                    break
            if empty_generation:
                return {'status': 'error', 'data': 'No connection found.'}


def get_parent_coords(sibling_group_coords, tree):
    """Sibling_group_coords is a list of the form [direction, generation, sibling_group_index].
Returns parent_coords as a list of the form [direction, generation, parent_group_index, parent_index_within_group].
Generation values are negative integers which index starting from last generation at -1.
TREE DATA STRUCTURE: tree[direction][generation][sibling_group_index][sibling_index]
(see get_tree() docstring for more info on tree data structure.)"""

    direction = sibling_group_coords[0]
    generation_index = sibling_group_coords[1]
    sibling_group_index = sibling_group_coords[2]

    parent_count_in_prev_groups = 0
    for parent_group_index in range(len(tree[direction][generation_index - 1])):
        parent_count_in_this_group = len(tree[direction][generation_index - 1][parent_group_index])
        if parent_count_in_this_group + parent_count_in_prev_groups < sibling_group_index + 1:
            parent_count_in_prev_groups += parent_count_in_this_group
        else:
            parent_index_within_group = sibling_group_index - parent_count_in_prev_groups
            parent_coords = [direction, generation_index - 1, parent_group_index, parent_index_within_group]
            return parent_coords


def get_genealogy_line(sibling_group_coords, tree):
    """Sibling_group_coords is a list of the form [direction, generation, sibling_group_index].
Returns genealogy_line as an ordered list of coordinates within tree for each generation.
Coordinates in genealogy_line are of the form [direction, generation, sibling_group_index, sibling_index_within_group].
Generation values are negative integers which index starting from last generation at -1.
TREE DATA STRUCTURE: tree[direction][generation][sibling_group_index][sibling_index]
(see get_tree() docstring for more info on tree data structure.)"""

    direction = sibling_group_coords[0]
    sibling_generation_index = sibling_group_coords[1]
    num_prev_generations = len(tree[direction]) + sibling_generation_index
    genealogy_line = [sibling_group_coords]

    for generation_index in range(num_prev_generations, 0, -1):
        parent_of_child = get_parent_coords(sibling_group_coords, tree)
        genealogy_line.insert(0, parent_of_child)
        sibling_group_coords = parent_of_child[:-1]

    return genealogy_line


def get_paths_from_tree(wordnet_data, tree):
    """Returns paths_by_connector as a dictionary where each key is the connecting synset_id of its path.
Each key-value is a path represented as an ordered list containing the path nodes.
Each path node is a dictionary with these data_keys:
'color_a', 'color_b', 'two_kw', 'key_words', 'other_words', 'pos', 'gloss', 'pointer_phrase'.
PATHS DATA STRUCTURE: paths_by_connector[connecting_synset_id][path_node_index][data_key]"""

    paths_by_connector = {}

    for direction in range(2):
        latest_generation = tree[direction][-1]
        for sibling_group_index in range(len(latest_generation)):
            genealogy_line = get_genealogy_line([direction, -1, sibling_group_index], tree)
            sibling_group = latest_generation[sibling_group_index]

            for sibling_index in range(len(sibling_group)):

                connecting_synset_id = sibling_group[sibling_index][1]

                if direction == 0:
                    paths_by_connector[connecting_synset_id] = []

                insert_index = len(paths_by_connector[connecting_synset_id])
                this_path = paths_by_connector[connecting_synset_id]
                gene_line_plus_sibling_index = deepcopy(genealogy_line)
                gene_line_plus_sibling_index[-1].append(sibling_index)

                # Populate this_path.
                for node_coords in gene_line_plus_sibling_index:
                    # Node_coords are of the form [direction, generation, sibling_group_index, sibling_index].
                    this_pointer = tree[node_coords[0]][node_coords[1]][node_coords[2]][node_coords[3]]

                    pointer_node = {
                        'pointer_source': this_pointer[2],
                        'pointer_target': this_pointer[3],
                        'pointer_phrase': POINTER_SYMBOL_KEY[this_pointer[0]]['phrase'],
                    }
                    synset_node = {'synset_id': this_pointer[1]}
                    if direction == 0:
                        this_path.append(pointer_node)
                        this_path.append(synset_node)
                    else:
                        this_path.insert(insert_index, pointer_node)
                        this_path.insert(insert_index, synset_node)

                # Remove connecting synset (last) in direction 0. Redundant; will be added in direction 1.
                if direction == 0:
                    this_path.pop(-1)

    for connecting_synset_id in paths_by_connector:
        path = paths_by_connector[connecting_synset_id]
        for node_index in range(len(path) - 2, 0, -2):

            this_node = path[node_index]
            prev_node = path[node_index - 1]
            next_node = path[node_index + 1]
            synset_id = this_node['synset_id']
            this_node['pointer_phrase'] = next_node['pointer_phrase']
            wordnet_data_this_synset = wordnet_data[synset_id]
            this_node['pos'] = wordnet_data_this_synset[1]
            this_node['gloss'] = wordnet_data_this_synset[2]

            all_words_underscored = wordnet_data_this_synset[3]
            all_words = []
            for word in all_words_underscored:
                formatted_word = word.replace('_', ' ').split('(')[0]
                all_words.append(formatted_word)

            key_words = []
            target_word_index = prev_node['pointer_target']
            if target_word_index != -1:
                target_word = all_words[target_word_index]
                key_words.append(target_word)
            source_word_index = next_node['pointer_source']
            if source_word_index != -1:
                source_word = all_words[source_word_index]
                if source_word not in key_words:
                    key_words.append(source_word)
            if len(key_words) == 0:
                key_words.append(all_words[0])
            this_node['key_words'] = key_words
            this_node['two_kw'] = len(key_words) == 2

            this_node['other_words'] = ''
            for word in all_words:
                if word not in key_words:
                    this_node['other_words'] += word
                    this_node['other_words'] += ', '
            this_node['other_words'] = this_node['other_words'][:-2]

            del this_node['synset_id']

        for node_index in range(len(path) - 1, -1, -2):
            del path[node_index]

        this_node_hue = START_HUE
        for node in path:
            node['color_a'] = f'hsl({this_node_hue}, 100%, 75%)'  # main background
            node['color_b'] = f'hsl({this_node_hue}, 100%, 78%)'  # ligher background for pointer between synsets
            node['color_c'] = f'hsl({this_node_hue}, 100%, 28%)'  # non-black text: part of speech,
            # pointer phrase, arrows
            this_node_hue = (this_node_hue + HUE_STEP) % 360

    return paths_by_connector


def web_app_inquiry(wordnet_data, wordnet_index, group_map, start_word, target_word):

    formatted_start_word = clean_string(start_word)
    formatted_target_word = clean_string(target_word)

    if formatted_start_word == '':
        return {'status': 'error', 'message': 'Please enter a start word.'}
    if formatted_target_word == '':
        return {'status': 'error', 'message': 'Please enter a target word.'}

    if formatted_start_word not in wordnet_index:
        return {'status': 'error', 'message': f"""I'm sorry, but "{start_word}" isn't in my database."""}
    if formatted_target_word not in wordnet_index:
        return {'status': 'error', 'message': f"""I'm sorry, but "{target_word}" isn't in my database."""}

    if formatted_start_word == formatted_target_word:
        message = 'Your start and target words are too similar to yield anything interesting.'
        return {'status': 'error', 'message': message}

    tree_result = get_tree(wordnet_data, wordnet_index, group_map, formatted_start_word, formatted_target_word)
    if tree_result['status'] != 'ok':
        message = f"""I'm sorry, but I couldn't find a path from "{start_word}" to "{target_word}"."""
        return {'status': 'error', 'message': message}

    result_paths = get_paths_from_tree(wordnet_data, tree_result['data'])

    path_length = 0
    for path in result_paths:
        path_length = len(result_paths[path])
        break

    path_s = 'paths'
    if len(result_paths) == 1:
        path_s = 'path'
    synsets_evaluated = tree_result["synsets_visited"]
    if synsets_evaluated >= 1000:
        synsets_evaluated = f'{int(synsets_evaluated / 1000)}K'
    message = f'Found {len(result_paths)} {path_s} of length {path_length}. Evaluated {synsets_evaluated} definitions.'
    result = {
        'status': 'ok',
        'message': message,
        'data': result_paths,
    }
    return result
