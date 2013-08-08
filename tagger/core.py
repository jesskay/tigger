import hashlib, os.path, string, tagger.error

_valid_tag_characters = (
        set(string.ascii_letters) |
        set(string.digits) |
        set([".", "-", "_", " "])
        )

_meta_dir_name = ".tagger-meta"

def initialize_base_dir(base_dir="."):
    base_dir = os.path.abspath(base_dir)
    os.makedirs(os.path.join(base_dir, _meta_dir_name, "files"))
    os.makedirs(os.path.join(base_dir, _meta_dir_name, "tags"))

def find_base_dir(start_dir="."):
    base_dir = os.path.abspath(start_dir)
    while not os.path.isdir(os.path.join(base_dir, _meta_dir_name)):
        if os.path.dirname(base_dir) == base_dir:  # can't go up
            raise tagger.error.NotInTaggedDir(start_dir)
        base_dir = os.path.dirname(base_dir)
    return base_dir

def is_valid_tag(name):
    return len(set(list(name)) - _valid_tag_characters) == 0

def tag_to_hash(name):
    if not is_valid_tag(name):
        raise tagger.error.InvalidTag(name)
    return hashlib.sha1(name.encode("utf-8")).hexdigest()

def tag_to_metapath(name):
    hash = tag_to_hash(name)
    return os.path.join(find_base_dir(),
            _meta_dir_name,
            "tags",
            hash[:2],
            name)

def file_path_normalize(name):
    file_path = os.path.abspath(name)
    if not file_path.startswith(find_base_dir()):
        raise tagger.error.NotInTaggedDir(file_path)
    else:
        return file_path.replace(find_base_dir(), "", 1)

def file_to_metapath(name):
    hash = hashlib.sha1(name.encode("utf-8")).hexdigest()
    return os.path.join(find_base_dir(),
            _meta_dir_name,
            "files",
            hash[:2])

def _file_update_tags(name, tags, action="add", propagate=False):
    tags = [tag.strip() for tag in tags]

    for tag in tags:
        if not is_valid_tag(tag):
            raise tagger.error.InvalidTag(tag)

    sought_file = file_path_normalize(name)
    tags_filename = file_to_metapath(sought_file)
    file_tag_map = {}

    with open(tags_filename, "r") as tags_file:
        for line in tags_file:
            try:
                file_name, old_tags = line.split("\0")
            except:
                continue

            old_tags = [tag.strip() for tag in old_tags.split(",")]
            if old_tags == [""]:
                old_tags = []

            if file_name == sought_file:
                if action == "add":
                    new_tag_set = set(old_tags) | set(tags)
                elif action == "remove":
                    new_tag_set = set(old_tags) - set(tags)
                else:
                    raise ValueError("Invalid operation: {}".format(action))

                if new_tag_set == set(old_tags):
                    return
                else:
                    file_tag_map[file_name] = sorted(new_tag_set)
            else:
                file_tag_map[file_name] = sorted(old_tags)

    with open(tags_filename, "w") as tags_file:
        for file_name in sorted(file_tag_map.keys()):
            if file_tag_map[file_name] != []:
                tags_file.write("{}\0{}\n".format(file_name,
                    ",".join(file_tag_map[file_name])))

    if propagate:
        for tag in tags:
            _tag_update_files(tag, [name], action)

def file_get_tags(name):
    sought_file = file_path_normalize(name)
    try:
        with open(file_to_metapath(sought_file), "r") as tags_file:
            for line in tags_file:
                try:
                    file_name, tags = line.split("\0")
                except ValueError:
                    continue

                tags = [tag.strip() for tag in tags.split(",")]

                if file_name == sought_file:
                    if tags == [""]:
                        tags = []
                    return tags
    except IOError as e:
        if e.errno == 2:  # no such file, assume no tags
            return []
        else:
            raise e

def file_add_tags(name, tags):
    return _file_update_tags(name, tags, "add", True)

def file_remove_tags(name, tags):
    return _file_update_tags(name, tags, "remove", True)

def _tag_update_files(tag, names, action="add", propagate=False):
    tag = tag.strip()
    names = [file_path_normalize(name) for name in names]

    tag_filename = tag_to_metapath(tag)
    tagged_files = set()

    try:
        with open(tag_filename, "r") as tag_file:
            for line in tag_file:
                if line.strip() != "":
                    tagged_files.add(line.strip())
    except IOError:
        pass  # tag doesn't exist, so we'll just be creating it

    if action == "add":
        tagged_files |= set(names)
    elif action == "remove":
        tagged_files -= set(names)

    try:
        os.makedirs(os.path.dirname(tag_filename))  # in case even the dir doesn't exist
    except:
        pass

    with open(tag_filename, "w") as tag_file:
        for name in sorted(tagged_files):
            tag_file.write("{}\n".format(name))

    if propagate:
        for name in names:
            _file_update_tags(name, [tag], action)

def tag_get_files(tag):
    tagged_files = set()

    try:
        with open(tag_to_metapath(tag), "r") as tag_file:
            for line in tag_file:
                tagged_files.add(line.strip())
    except IOError as e:
        if e.errno == 2:  # no such file, assume no tags
            return []
        else:
            raise e

    return sorted(tagged_files)

def tag_add_files(tag, names):
    return _tag_update_files(tag, names, "add", True)

def tag_remove_files(tag, names):
    return _tag_update_files(tag, names, "remove", True)