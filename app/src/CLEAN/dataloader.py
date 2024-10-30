import torch
import random
from .utils import format_esm
from tqdm import tqdm

def find_first_non_zero_distance(data):
    for index, (name, distance) in enumerate(data):
        if distance != 0:
            return index
    return None 

def mine_hard_negative(dist_map, knn=10):
    #print("The number of unique EC numbers: ", len(dist_map.keys()))
    ecs = list(dist_map.keys())
    negative = {}
    print("Mining hard negatives:")
    for _, target in tqdm(enumerate(ecs), total=len(ecs)):
        sorted_orders = sorted(dist_map[target].items(), key=lambda x: x[1], reverse=False)
        assert sorted_orders != None, "all clusters have zero distances!"
        neg_ecs_start_index = find_first_non_zero_distance(sorted_orders)
        closest_negatives = sorted_orders[neg_ecs_start_index:neg_ecs_start_index + knn]
        freq = [1/i[1] for i in closest_negatives]
        neg_ecs = [i[0] for i in closest_negatives]        
        normalized_freq = [i/sum(freq) for i in freq]
        negative[target] = {
            'weights': normalized_freq,
            'negative': neg_ecs
        }
    return negative


def mine_negative(anchor, id_ec, ec_id, mine_neg):
    anchor_ec = id_ec[anchor]
    pos_ec = random.choice(anchor_ec)
    neg_ec = mine_neg[pos_ec]['negative']
    weights = mine_neg[pos_ec]['weights']
    result_ec = random.choices(neg_ec, weights=weights, k=1)[0]
    while result_ec in anchor_ec:
        result_ec = random.choices(neg_ec, weights=weights, k=1)[0]
    neg_id = random.choice(ec_id[result_ec])
    return neg_id


def random_positive(id, id_ec, ec_id):
    pos_ec = random.choice(id_ec[id])
    pos = id
    if len(ec_id[pos_ec]) == 1:
        return pos + '_' + str(random.randint(0, 9))
    while pos == id:
        pos = random.choice(ec_id[pos_ec])
    return pos


class Triplet_dataset_with_mine_EC(torch.utils.data.Dataset):

    def __init__(self, id_ec, ec_id, mine_neg, dir_name='cmu_idl_dir_name', batch_size=256, use_new_full_method=True):
        self.id_ec = id_ec
        self.ec_id = ec_id
        self.full_list = []
        self.mine_neg = mine_neg
        self.dir_name = dir_name

        if use_new_full_method:
            print('new full list method')
            for _ in range(batch_size):
                # Randomly select an id from id_ec keys
                random_id = random.choice(list(self.id_ec.keys()))
                # Randomly select an ec from the list associated with this id
                if isinstance(self.id_ec[random_id], list):
                    random_ec = random.choice(self.id_ec[random_id])
                    self.full_list.append(random_ec)
        else:
            print('old full list method')
            for ec in ec_id.keys():
                if '-' not in ec:
                    self.full_list.append(ec)

    def __len__(self):
        return len(self.full_list)

    def __getitem__(self, index):
        anchor_ec = self.full_list[index]
        anchor = random.choice(self.ec_id[anchor_ec])
        pos = random_positive(anchor, self.id_ec, self.ec_id)
        neg = mine_negative(anchor, self.id_ec, self.ec_id, self.mine_neg)
        a = torch.load('./data/' + self.dir_name + '/' + anchor + '.pt')
        p = torch.load('./data/' + self.dir_name + '/' + pos + '.pt')
        n = torch.load('./data/' + self.dir_name + '/' + neg + '.pt')
        return format_esm(a), format_esm(p), format_esm(n)


class MultiPosNeg_dataset_with_mine_EC(torch.utils.data.Dataset):

    def __init__(self, id_ec, ec_id, mine_neg, n_pos, n_neg):
        self.id_ec = id_ec
        self.ec_id = ec_id
        self.n_pos = n_pos
        self.n_neg = n_neg
        self.full_list = []
        self.mine_neg = mine_neg
        for ec in ec_id.keys():
            if '-' not in ec:
                self.full_list.append(ec)

    def __len__(self):
        return len(self.full_list)

    def __getitem__(self, index):
        anchor_ec = self.full_list[index]
        anchor = random.choice(self.ec_id[anchor_ec])
        a = format_esm(torch.load('./data/esm_data/' +
                       anchor + '.pt')).unsqueeze(0)
        data = [a]
        for _ in range(self.n_pos):
            pos = random_positive(anchor, self.id_ec, self.ec_id)
            p = format_esm(torch.load('./data/esm_data/' +
                           pos + '.pt')).unsqueeze(0)
            data.append(p)
        for _ in range(self.n_neg):
            neg = mine_negative(anchor, self.id_ec, self.ec_id, self.mine_neg)
            n = format_esm(torch.load('./data/esm_data/' +
                           neg + '.pt')).unsqueeze(0)
            data.append(n)
        return torch.cat(data)
