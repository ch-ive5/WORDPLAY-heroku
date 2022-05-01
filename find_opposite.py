import colorsys
import random
import manage_database
import find_connection
from copy import deepcopy


POINTER_SYMBOL_KEY = manage_database.POINTER_SYMBOL_KEY
POINTER_TYPES_TO_IGNORE = manage_database.POINTER_TYPES_TO_IGNORE
IGNORE_ANTONYMS = manage_database.IGNORE_ANTONYMS
POINTER_SEQUENCES_TO_IGNORE = manage_database.POINTER_SEQUENCES_TO_IGNORE


def hsv_to_hsl(hsv):
    h, s, v = hsv
    rgb = colorsys.hsv_to_rgb(h/360, s/100, v/100)
    r, g, b = rgb
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h*360, s*100, l*100


def get_tree_to_nearest_antonyms(wordnet_data, groups_without_opposites, start_word, start_synset_ids):
    """Returns a "tree", or a list of recursively nested lists encoding various paths from start to end synsets.

Start_word should be lower case, and spaces should be replaced with underscores.

Returns dictionary with keys "status" and "data". Status can be "ok" or "error".
If status is ok, data is path_memory tree. If status is error, data is a string describing the error.

TREE DATA STRUCTURE: tree[direction][generation][sibling_group_index][sibling_index]
    DIRECTION: Always 0. Vestigial from find_connection, and needed to be compatible with other functions.
    GENERATION: 0 is the first/oldest generation where branching begins at start and end synsets.
    -1 is last/newest generation where connecting synsets are found in common for both directions.
    SIBLING GROUP INDEX: Index of sibling group, containing pointers from the same parent synset in previous generation.
    SIBLING_INDEX: Index of pointer within sibling group."""

    def prune_tree(synset_connectors):
        """Removes pointers not part of synset_connectors paths, empty pointer child groups,
and parent pointers with no children from path_memory.
Synset_connectors is list of synset_ids to keep in last generation.
Pass in empty list to synset_connectors if no connection found yet."""

        connection_after_prune = False

        # If connection found this iteration, delete any non-connecting pointers from last generation.
        if len(synset_connectors) > 0:
            connection_after_prune = True

            # Log all antonyms of synsets to see if any antonym pairs exist to delete both.
            antonyms_of_antonyms = []
            for sibling_group_index in range(len(path_memory[0][-1])):
                for sibling_index in range(len(path_memory[0][-1][sibling_group_index])):
                    pointer = path_memory[0][-1][sibling_group_index][sibling_index]
                    if pointer[1] in synset_connectors and pointer[0] == '!':
                        possible_antonym = wordnet_data[pointer[1]][4][0]
                        if possible_antonym[0] == '!':
                            # Add antonym of antonym to list.
                            antonyms_of_antonyms.insert(0, possible_antonym[1])

            sibling_indices_to_delete = []
            num_synsets_this_generation = 0
            for sibling_group_index in range(len(path_memory[0][-1])):
                for sibling_index in range(len(path_memory[0][-1][sibling_group_index])):
                    num_synsets_this_generation += 1
                    pointer = path_memory[0][-1][sibling_group_index][sibling_index]
                    if pointer[1] not in synset_connectors or pointer[0] != '!' or pointer[1] in antonyms_of_antonyms:
                        # Add non-antonym pointers to delete queue.
                        sibling_indices_to_delete.insert(0, [sibling_group_index, sibling_index])

            if len(sibling_indices_to_delete) >= num_synsets_this_generation:
                # Prevents deleting entire generation.
                connection_after_prune = False
                sibling_indices_to_delete = []
                for sibling_group_index in range(len(path_memory[0][-1])):
                    for sibling_index in range(len(path_memory[0][-1][sibling_group_index])):
                        if path_memory[0][-1][sibling_group_index][sibling_index][0] == '!':
                            # Add antonym pointers to delete queue.
                            sibling_indices_to_delete.insert(0, [sibling_group_index, sibling_index])

            # Delete pointers in queue. Either all antonym or all non-antonym pointers.
            for sibling_index in sibling_indices_to_delete:
                del path_memory[0][-1][sibling_index[0]][sibling_index[1]]

        # Prune empty sibling groups and parents of empty sibling groups.
        for generation in range(len(path_memory[0]) - 1):

            # Initialize delete queues.
            empty_sibling_groups = []  # List of sibling group indices to delete in current generation.
            parents_without_children = []  # List of parent coordinates to delete in previous generation.
            # Each coordinate is encoded as a list: [parent_group_index, parent_index_within_group]

            # Add empty sibling groups and parents without children to delete queues.
            for sibling_group_index in range(len(path_memory[0][-1 - generation])):
                if len(path_memory[0][-1 - generation][sibling_group_index]) == 0:
                    # Run if sibling group is empty.
                    empty_sibling_groups.insert(0, sibling_group_index)  # Add sibling group to delete queue.
                    sibling_group_coords = [0, -1 - generation, sibling_group_index]
                    parent_coords = find_connection.get_parent_coords(sibling_group_coords, path_memory)[2:]
                    parents_without_children.insert(0, parent_coords)

            # Delete empty sibling groups and parents without children listed in delete queues.
            for sibling_group_index in empty_sibling_groups:
                del path_memory[0][-1 - generation][sibling_group_index]
            for parent_coords in parents_without_children:
                parent_group_index = parent_coords[0]
                parent_index_within_group = parent_coords[1]
                del path_memory[0][-2 - generation][parent_group_index][parent_index_within_group]

        return connection_after_prune

    start_pointers_list = []
    for synset_id in start_synset_ids:
        group_num = wordnet_data[synset_id][0]
        if group_num in groups_without_opposites:
            continue
        lower_case_words = [word.lower().split('(')[0] for word in wordnet_data[synset_id][3]]
        word_index = lower_case_words.index(start_word)
        child_pointer = ('__start', synset_id, word_index, word_index)
        start_pointers_list.append(child_pointer)

    if len(start_pointers_list) == 0:
        message = 'No reachable antonyms exist.'
        return {'status': 'error', 'data': message}

    path_memory = [[[start_pointers_list]]]
    visited_synsets = set(start_synset_ids)
    found_connection = False
    connecting_synsets = set()

    while True:  # Each loop is one layer in a breadth-first search.

        next_generation = []

        for parent_group in path_memory[0][-1]:  # Getting pointer groupings from previous generation.
            for parent_pointer in parent_group:  # Find neighbor_synsets of synsets_currently_visiting.

                sibling_group = []

                parent_synset_id = parent_pointer[1]
                for child_pointer in wordnet_data[parent_synset_id][4]:

                    child_pointer_symbol = child_pointer[0]
                    if child_pointer_symbol in POINTER_TYPES_TO_IGNORE or child_pointer_symbol == '?p':
                        continue  # Ignore specified pointers and word pivots.

                    if parent_pointer[0] in POINTER_SEQUENCES_TO_IGNORE:
                        if POINTER_SEQUENCES_TO_IGNORE[parent_pointer[0]] == child_pointer_symbol:
                            continue  # Ignore specified pointer type sequences.

                    child_pointer_id = child_pointer[1]

                    if child_pointer_symbol == '!' and child_pointer_id not in connecting_synsets:
                        found_connection = True
                        connecting_synsets.add(child_pointer_id)

                    # Add pointer to tree if not yet visited OR if it's an antonym.
                    if child_pointer_id not in visited_synsets or child_pointer_id in connecting_synsets:
                        sibling_group.append(child_pointer)

                    # Add pointer to visited_synsets.
                    visited_synsets.add(child_pointer_id)

                next_generation.append(sibling_group)

        empty_generation = True
        for sibling_group in next_generation:
            if len(sibling_group) > 0:
                empty_generation = False
                break
        if empty_generation:
            message = 'Reached dead-end in path. Failure in either earlier check for existence ' \
                      'of reachable antonym, or failure in iterating paths.'
            return {'status': 'error', 'data': message}

        path_memory[0].append(next_generation)

        after_prune_found_connection = prune_tree(connecting_synsets)
        if found_connection and not after_prune_found_connection:
            found_connection = False
            connecting_synsets = set()

        if found_connection:
            return {'status': 'ok', 'data': path_memory}


def get_paths_from_antonym_tree(wordnet_data, tree):
    """Returns paths_by_connector as a dictionary where each key is the connecting synset_id of its path.
Each key-value is a path represented as an ordered list containing the path nodes.
Each path node is a dictionary with these data_keys:
'color_a', 'color_b', 'two_kw', 'key_words', 'other_words', 'pos', 'gloss', 'pointer_phrase'.
PATHS DATA STRUCTURE: paths_by_connector[connecting_synset_id][path_node_index][data_key]"""

    paths_by_connector = {}

    latest_generation = tree[0][-1]
    for sibling_group_index in range(len(latest_generation)):
        genealogy_line = find_connection.get_genealogy_line([0, -1, sibling_group_index], tree)
        sibling_group = latest_generation[sibling_group_index]

        for sibling_index in range(len(sibling_group)):

            connecting_synset_id = sibling_group[sibling_index][1]

            paths_by_connector[connecting_synset_id] = []

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
                this_path.append(pointer_node)
                this_path.append(synset_node)

            # Add end pointer.
            end_pointer = {
                'pointer_source': -1,
                'pointer_target': -1,
                'pointer_phrase': POINTER_SYMBOL_KEY['__end']['phrase'],
            }
            this_path.append(end_pointer)

    this_path_hue = random.randint(0, 360)

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

        this_path_hue = (this_path_hue - 110) % 360
        soft_text_value = 35
        start_lightness = 50
        end_lightness = 100
        lightness_change_relative = len(path) * 2 - 4
        lightness_change_absolute = (end_lightness - start_lightness) / max(lightness_change_relative, 1)

        for node_index in range(len(path)):
            node = path[node_index]

            if node_index + 1 == len(path):  # final node
                node['color_a'] = f'hsl(0, 0%, 30%)'  # main background
                node['color_c'] = f'hsl(0, 0%, {100 - soft_text_value + 15}%)'  # softer text: part of speech,
                # pointer phrase, arrows
                node['color_d'] = f'hsl(0, 0%, 100%)'  # main text: words, gloss
            elif len(path) == 2:  # first node in 2-node path
                c_saturation = 200 - end_lightness * 2
                c_hsl = hsv_to_hsl([this_path_hue, c_saturation, soft_text_value])
                node['color_a'] = f'hsl({this_path_hue}, 100%, {end_lightness}%)'  # main background
                node['color_c'] = f'hsl({c_hsl[0]}, {c_hsl[1]}%, {c_hsl[2]}%)'  # softer text: part of speech,
                # pointer phrase, arrows
                node['color_d'] = f'hsl({this_path_hue}, 100%, 0%)'  # main text: words, gloss
            else:  # not final node
                a_lightness = start_lightness + lightness_change_absolute * (node_index * 2)
                c_saturation = 200 - a_lightness * 2
                c_hsl = hsv_to_hsl([this_path_hue, c_saturation, soft_text_value])
                node['color_a'] = f'hsl({this_path_hue}, 100%, {a_lightness}%)'  # main background
                node['color_c'] = f'hsl({c_hsl[0]}, {c_hsl[1]}%, {c_hsl[2]}%)'  # softer text: part of speech,
                # pointer phrase, arrows
                node['color_d'] = f'hsl({this_path_hue}, 100%, 0%)'  # main text: words, gloss

            # ligher background for pointer between synsets
            if node_index + 2 == len(path):  # penultimate node
                node['color_b'] = f'hsl({(this_path_hue - 10) % 360}, 0%, 75%)'
            else:  # not penultimate node
                b_lightness = start_lightness + lightness_change_absolute * (node_index * 2 + 1)
                node['color_b'] = f'hsl({(this_path_hue - 10) % 360}, 100%, {b_lightness}%)'

    return paths_by_connector


def web_app_inquiry(wordnet_data, wordnet_index, groups_without_opposites, start_word, start_synset):

    formatted_start_word = find_connection.clean_string(start_word)

    if formatted_start_word == '':
        return {'status': 'error', 'message': 'Please enter a word.'}

    if start_synset == '':

        if formatted_start_word not in wordnet_index:
            return {'status': 'error', 'message': f"""I'm sorry, but "{start_word}" isn't in my database."""}

        start_synsets = wordnet_index[formatted_start_word]

        if len(start_synsets) > 1:
            data = {}
            none_have_path = True
            for synset_id in start_synsets:
                synset_data = wordnet_data[synset_id]
                if synset_data[0] not in groups_without_opposites:
                    none_have_path = False
                key_words = ''
                for word in synset_data[3]:
                    formatted_word = word.replace('_', ' ').split('(')[0]
                    key_words += f'{formatted_word}, '
                key_words = key_words[:-2]
                data[synset_id] = {
                    'key_words': key_words,
                    'pos': synset_data[1],
                    'gloss': synset_data[2],
                }
            if none_have_path:
                message = f"""I'm sorry, but I couldn't find a quasi-opposite for "{start_word}"."""
                result = {'status': 'error', 'message': message}
            else:
                result = {
                    'status': 'choose_synset',
                    'message': f'Choose a meaning for "{start_word}"...',
                    'data': data,
                }
            return result

        tree_result = get_tree_to_nearest_antonyms(
            wordnet_data, groups_without_opposites, formatted_start_word, start_synsets)

    else:
        tree_result = get_tree_to_nearest_antonyms(
            wordnet_data, groups_without_opposites, formatted_start_word, [int(start_synset)])

    if tree_result['status'] != 'ok':
        message = f"I'm sorry, but I couldn't find a quasi-opposite for that meaning."
        return {'status': 'error', 'message': message}

    result_paths = get_paths_from_antonym_tree(wordnet_data, tree_result['data'])

    path_length = 0
    for path in result_paths:
        path_length = len(result_paths[path])
        break

    opposite_s = 'opposites'
    if len(result_paths) == 1:
        opposite_s = 'opposite'
    message = f'Found {len(result_paths)} quasi-{opposite_s} of degree {path_length - 1}.'
    if path_length < 3:
        message = """There already exists an established "degree 1" antonym relationship. """ \
                  """You can try words that aren't normally thought of as having an opposite."""
    result = {
        'status': 'ok',
        'message': message,
        'data': result_paths,
    }
    return result
