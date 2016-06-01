#!/bin/python3

"""%prog [--help] <e1> <e1_begin> <e1_end> <e2> <e2_begin> <e2_end> [<"sentence">]"""

import sys
from delphin.interfaces import ace
from delphin.mrs import simplemrs

__author__ = 'Martin J. Horn'


#announced716closed5258=:=feats delminited by spaces
#NO_FEATS

def output_features(features):
    str = ""
    for feat in features:
        str += feat + " "
    print(str)
    sys.stdout.flush()


def extract_features(e1, e1_b, e1_e, e2, e2_b, e2_e, ace_result, reversed):
    # print("a1"+ace_result)
    features = []
    mrs = simplemrs.loads_one(ace_result)
    # print("mrs obj:" + str(mrs))
    ep_1, ep_2 = None, None
    for ep in mrs.eps():
        # print("an ep:" + str(ep))
        # print("is (ep.cfrom=", ep.cfrom, ") <= (e1_b=", e1_b+1, ") <= (ep.cto",
        #       ep.cto, ")? ", ep.cfrom <= e1_b <= ep.cto,
        #       " AND, (ep.pred.pos == 'n' or ep.pred.pos == 'v')? ",
        #       (ep.pred.pos == 'n' or ep.pred.pos == 'v'))
        if ep.cfrom <= e1_b + 1 <= ep.cto and (ep.pred.pos == 'n' or ep.pred.pos == 'v' or ep.pred.pos == 'a'):
            # print(str(ep) + "matched with " ,str(e1))
            ep_1 = ep
            continue
        elif ep.cfrom <= e2_b + 1 <= ep.cto and (ep.pred.pos == 'n' or ep.pred.pos == 'v' or ep.pred.pos == 'a'):
            # print(str(ep) + "matched with " ,str(e2))
            ep_2 = ep
            break
            # if ep:
            #     ep_1=ep
            #     #print("ep1 declared")
            # if ep:
            #     ep_2=ep
            #     #print("ep2 declared")

    # print("a2")
    if ep_1 and ep_2:
        if reversed:
            e1_tag = "e2"
            e2_tag = "e1"
        else:
            e1_tag = "e1"
            e2_tag = "e2"
        # print("a3")
        features.extend(get_lemmas(ep_1, ep_2, e1_tag, e2_tag))
        features.extend(get_properties(mrs, ep_1, ep_2, e1_tag, e2_tag))
        features.extend(find_temp_preds(mrs, ep_1, ep_2, e1_tag, e2_tag))

        paths = find_paths(mrs, ep_1, ep_2, e1_tag, e2_tag, "")

        if paths:
            shortest_path = paths[0]
            for path in paths:
                if len(path.split(",")) < len(shortest_path.split(",")):
                    shortest_path = path
        else:
            shortest_path = "NO_PATH"
        features.append("PATH=" + shortest_path)

    # print("a6")
    return features


def find_temp_preds(mrs, ep_1, ep_2, e1_tag, e2_tag):
    features = []
    modal = "_modal"
    temp_preds = ["_after", "_before", "_during", "_while",
                  "_until", "temp_loc_x", "_when_x_subord",
                  "_once_x_subord", "_as_x_subord", "_since_x_subord"]

    for ep in mrs.eps():
        e1_found = False
        e2_found = False
        for pred in temp_preds:
            if pred in ep.pred.string or modal in ep.pred.string:
                pred_args = mrs.outgoing_args(ep.nodeid)
                for arg in pred_args:
                    labels = mrs.labelset(pred_args[arg])
                    if pred_args[arg] == ep_1.label or ep_1.label in mrs.labelset(pred_args[arg]):
                        e1_found = True
                    elif pred_args[arg] == ep_2.label:
                        e2_found = True

                if e1_found and e2_found:
                    feat = e1_tag + "#" + ep.pred + "#" + e2_tag
                    features.append(feat)

    return features


def get_lemmas(ep_1, ep_2, e1_tag, e2_tag):
    features = []
    feat_1 = e1_tag + "LEMMA=" + ep_1.pred.lemma
    feat_2 = e2_tag + "LEMMA=" + ep_2.pred.lemma
    features.append(feat_1)
    features.append(feat_2)

    return features


def get_properties(mrs, ep_1, ep_2, e1_tag, e2_tag):
    features = []
    for prop in mrs.properties(ep_1.iv):
        feat = e1_tag + prop + "=" + mrs.properties(ep_1.iv)[prop]
        features.append(feat)
    for prop in mrs.properties(ep_2.iv):
        feat = e2_tag + prop + "=" + mrs.properties(ep_2.iv)[prop]
        features.append(feat)

    return features


seen_ids = set()


def find_paths(mrs, ep_1, ep_2, e1_tag, e2_tag, cur_path, count=0):
    # Recursive path search using incoming args of second event
    paths = []
    if len(cur_path) == 0:
        if ep_2.pred.pos:
            cur_path = e2_tag + "#" + ep_2.pred.pos
        else:
            cur_path = e2_tag + "#" + "NO_POS"
            # Debug line: pred name
            # cur_path = ep_2.pred.string.strip("\"")
    else:
        if ep_2.pred.pos:
            cur_path = ep_2.pred.pos + "," + cur_path
        else:
            cur_path = "NO_POS," + cur_path
            # Debug line: pred name
            # cur_path = ep_2.pred.string.strip("\"") + "," + cur_path
    in_args = mrs.incoming_args(ep_2.nodeid)

    for node_id in in_args:
        global seen_ids
        if node_id not in seen_ids and count < 10:
            if mrs.ep(node_id).label != ep_1.label and mrs.ep(node_id).iv != ep_1.iv:
                for arg in in_args[node_id]:
                    prefix = arg + "#"
                    break
                seen_ids.add(node_id)
                count += 1
                paths += find_paths(mrs, ep_1, mrs.ep(node_id), e1_tag, e2_tag, prefix + cur_path, count)
            else:
                for arg in in_args[node_id]:
                    prefix = arg + "#"
                    break
                if mrs.ep(node_id).pred.pos:
                    cur_path = e1_tag + "#" + mrs.ep(node_id).pred.pos + "," + prefix + cur_path
                else:
                    cur_path = e1_tag + "#" + "NO_POS," + prefix + cur_path
                # Debug line: pred name
                # cur_path = mrs.ep(node_id).pred.string.strip("\"") + "," + prefix + cur_path
                paths.append(cur_path)
        # else:
        #     paths.clear()

    return paths


def run_ace(sentence):
    ace_bin = "/Applications/ace/ace-0.9.22/ace"
    erg_file = "/Applications/ace/ace-0.9.22/erg-1214-osx-0.9.22.dat"
    results = ace.parse(erg_file, sentence, cmdargs=['-n', '1'], executable=ace_bin)['RESULTS']
    if results:
        res1 = results[0]['MRS']
        with open("Data/demo_mrs.txt", 'w') as demo:
            demo.write(res1 + "\n")
    else:
        res1 = None

    return res1


def find_sentence(e1, e1_begin, e1_end, e2, e2_begin, e2_end, sent, cached_sent_file):
    index = None
    search_key = "#-#".join((e1, str(e1_begin), str(e1_end), e2, str(e2_begin), str(e2_end), sent))
    with open(cached_sent_file, 'r') as cached_sents:
        for i, line in enumerate(cached_sents.readlines()):
            if line.strip() == search_key:
                index = i

    return index


def read_mrs(index, cached_mrs_file):
    mrs_string = None

    if index is not None:
        with open(cached_mrs_file, 'r') as cached_mrs:
            mrs_lines = cached_mrs.readlines()
            if index < len(mrs_lines):
                mrs_string = mrs_lines[index]

    return mrs_string


def read_doc(e1, e1_begin, e1_end, e2, e2_begin, e2_end, file_name=None):
    reversed = False
    # Ensure e1 occurs first, e2 occurs second
    if int(e1_begin) < int(e2_begin):
        e1_string = e1
        e1_begin_sent = int(e1_begin)
        e1_end_sent = int(e1_end)
        e2_string = e2
        e2_begin_sent = int(e2_begin)
        e2_end_sent = int(e2_end)
    else:
        reversed = True
        e1_string = e2
        e1_begin_sent = int(e2_begin)
        e1_end_sent = int(e2_end)
        e2_string = e1
        e2_begin_sent = int(e1_begin)
        e2_end_sent = int(e1_end)

    # Check for specified input file
    if file_name:
        sent = file_name
        # # Read sentence from file
        # with open(file_name, 'r') as doc:
        #     doc_text = doc.read()
        #     sent = doc_text.strip()
    else:
        # Read sentence from stdin
        sent = input()

    return e1_string, e1_begin_sent, e1_end_sent, e2_string, e2_begin_sent, e2_end_sent, sent, reversed


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(__doc__)
    options, args = parser.parse_args()
    if len(args) == 6:
        e1, e1_b, e1_e, e2, e2_b, e2_e, sent, reversed = read_doc(args[0], args[1],
                                                        args[2], args[3],
                                                        args[4], args[5])
        res = run_ace(sent)
        # cache_file = "Data/cachedSentences.out"
        # cache_file = "Data/demo_sent.txt"
        # sent_index = find_sentence(e1, e1_b, e1_e, e2, e2_b, e2_e, sent, cache_file)
        # res = read_mrs(sent_index, "Data/demo_mrs.txt")
        if res:
            feats = extract_features(e1, e1_b, e1_e, e2, e2_b, e2_e, res, reversed)
            output_features(feats)
        else:
            print("NO_PARSE")

    if len(args) == 7:
        e1, e1_b, e1_e, e2, e2_b, e2_e, sent, reversed = read_doc(args[0], args[1],
                                                        args[2], args[3],
                                                        args[4], args[5],
                                                        file_name=args[6])
        res = run_ace(sent)
        # cache_file = "Data/cachedSentences.out"
        # cache_file = "Data/demo_sent.txt"
        # sent_index = find_sentence(e1, e1_b, e1_e, e2, e2_b, e2_e, sent, cache_file)
        # res = read_mrs(sent_index, "Data/demo_mrs.txt")
        if res:
            feats = extract_features(e1, e1_b, e1_e, e2, e2_b, e2_e, res, reversed)
            output_features(feats)
        else:
            print("NO_PARSE")
    else:
        sys.stderr.write("Must specify 6/7 arguments: <e1> <e1_begin> <e1_end> "
                         "<e2> <e2_begin> <e2_end> [<\"sentence\">]\n")