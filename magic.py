# coding: utf-8
import numpy as np
import pandas as pd
from collections import Counter
from scipy.stats import entropy


def magic(df):
    
    df.Click_time = df.Click_time.astype(int)
    df.id = df.id.astype(int)

    df = df.sort_values('Click_time')

    user_penalty = df.User_id.value_counts().reset_index()
    user_penalty.columns = ['User_id', 'n_user_clicks']
    user_penalty['penalty_n_user_clicks'] = np.sqrt(user_penalty.n_user_clicks - 1)

    user_n_ip = df.groupby('User_id')['User_IP'].nunique().reset_index()
    user_n_ip['penalty_n_user_ip'] = np.sqrt(user_n_ip.User_IP - 1)

    user_penalty = pd.merge(user_penalty, user_n_ip, on='User_id')

    df_podozr = df[df.User_id.isin(user_penalty.User_id[user_penalty.n_user_clicks >= 5])]
    clicks_time_median = df_podozr.groupby('User_id')['Click_time'].apply(lambda x: np.median(np.diff(x))).reset_index()
    clicks_time_median = clicks_time_median[clicks_time_median.Click_time <=
                                            clicks_time_median.Click_time.median()]

    clicks_time_median['penalty_clk_time'] = 10 / np.log(clicks_time_median.Click_time + 2)

    user_penalty = pd.merge(user_penalty, clicks_time_median, on='User_id', how='left')
    user_penalty.penalty_clk_time.fillna(0, inplace=True)

    diff_clk_time = df[df.User_id.isin(user_penalty.User_id[user_penalty.n_user_clicks > 1])]\
        .groupby(['User_id'])['Click_time']\
        .apply(lambda x: np.min(np.diff(x)))

    user_penalty['clicks2_in_3sec'] = user_penalty.User_id.isin(
        diff_clk_time[diff_clk_time <= 3].keys()
    ).astype(int) * 2

    diff_clk_time_diff = df_podozr.groupby('User_id')['Click_time'].apply(lambda x: np.max(x) - np.min(x))

    user_penalty['pen_big_in_15min'] = 0
    user_penalty.loc[user_penalty.User_id.isin(diff_clk_time_diff[diff_clk_time_diff < 15 * 60].keys()),
                     'pen_big_in_15min'] = 2

    user_penalty['penalty_user_sum'] = user_penalty.penalty_clk_time + user_penalty.penalty_n_user_clicks +\
                                       user_penalty.penalty_n_user_ip + user_penalty.clicks2_in_3sec +\
                                       user_penalty.pen_big_in_15min

    bad_users = user_penalty.User_id[
        user_penalty.penalty_user_sum >=
        np.percentile(user_penalty.penalty_user_sum[user_penalty.penalty_user_sum > 0], 98)
    ]

    sites = df.User_id.isin(bad_users).groupby(df.Site_id).mean()

    sites_clks = df.Site_id.value_counts().reset_index()
    sites_clks.columns = ['Site_id', 'n_sites_clck']

    sites_penalty = (sites[sites >= np.percentile(sites, 95)] * 20).reset_index()
    sites_penalty.columns = ['Site_id', 'penalty']

    sites_penalty = pd.merge(sites_clks, sites_penalty, on='Site_id', how='left')
    sites_penalty.penalty.fillna(0, inplace=True)

    site_ip = df.groupby('Site_id')[['User_id', 'User_IP']].nunique().reset_index()
    site_ip['ip_per_user'] = site_ip.User_IP / site_ip.User_id

    podozr_site = site_ip.Site_id[(site_ip.ip_per_user > 1.1) & ((site_ip.User_id >= 10) | (site_ip.User_IP >= 10))]
    podozr_site = podozr_site.append(
        site_ip.Site_id[(site_ip.ip_per_user <= 0.95) & ((site_ip.User_id >= 10) | (site_ip.User_IP >= 10))])

    sites_penalty['pen_strange_ip'] = 0
    sites_penalty.loc[sites_penalty.Site_id.isin(podozr_site), 'pen_strange_ip'] = 2

    site_click_from_first = df.groupby('Site_id')['User_id'].apply(
        lambda x: np.max(list(Counter(x).values())) / float(len(x)) if len(x) > 10 else -1)

    first_clk_penalty = (site_click_from_first[site_click_from_first > 0.1] * 20).reset_index()
    first_clk_penalty.columns = ['Site_id', 'pen_first_clk']
    sites_penalty = pd.merge(sites_penalty, first_clk_penalty, on='Site_id', how='left')
    sites_penalty.pen_first_clk.fillna(0, inplace=True)

    site_click_from_first3 = df.groupby('Site_id')['User_id'].apply(
        lambda x: sum(sorted(list(Counter(x).values()))[-3:]) / float(len(x)) if len(x) >= 30 else -1)

    first3_clk_penalty = (site_click_from_first3[site_click_from_first3 > 0.2] * 10).reset_index()
    first3_clk_penalty.columns = ['Site_id', 'pen_first3_clk']
    sites_penalty = pd.merge(sites_penalty, first3_clk_penalty, on='Site_id', how='left')
    sites_penalty.pen_first3_clk.fillna(0, inplace=True)

    min_t = df.Click_time.min()
    max_t = df.Click_time.max()

    x, y = np.histogram(df.Click_time, bins=10, range=(min_t, max_t), density=False)

    site_time_entropy = pd.DataFrame(columns=['Site_id', 'entropy'])

    for site in sites_clks.Site_id[sites_clks.n_sites_clck >= 100]:
        x2, y2 = np.histogram(df.Click_time[df.Site_id == site], bins=10, range=(min_t, max_t), density=False)
        site_time_entropy = site_time_entropy.append({
            'Site_id': site,
            'entropy': entropy(x / float(sum(x)), x2 / float(sum(x2)))
        }, ignore_index=True)

    site_time_entropy = site_time_entropy[np.isfinite(site_time_entropy.entropy)]

    site_time_entropy['penalty_entropy'] = 0
    site_time_entropy.loc[
        site_time_entropy.entropy >
        np.percentile(site_time_entropy.entropy, 90),
        'penalty_entropy'
    ] = 10 * site_time_entropy.entropy

    sites_penalty = pd.merge(sites_penalty, site_time_entropy[['Site_id', 'penalty_entropy']],
                             on='Site_id', how='left')
    sites_penalty.penalty_entropy.fillna(0, inplace=True)

    sites_penalty['penalty_site_sum'] = sites_penalty.loc[
                                        :,
                                        [
                                            'Site_id', 'penalty', 'pen_strange_ip',
                                            'pen_first_clk', 'pen_first3_clk',
                                            'penalty_entropy'
                                        ]
                                        ].sum(axis=1)

    ip_penalty = df.User_IP.value_counts().reset_index()
    ip_penalty.columns = ['User_IP', 'n_clks']

    ip_penalty['penalty_clks'] = np.log(ip_penalty.n_clks)
    ips_users = np.log(df.groupby('User_IP')['User_id'].nunique()).reset_index()
    ips_users.columns = ['User_IP', 'pen_uniqs']
    ip_penalty = pd.merge(ip_penalty, ips_users, on='User_IP')
    ip_penalty['penalty_ip_sum'] = ip_penalty.penalty_clks + ip_penalty.pen_uniqs

    df = pd.merge(df, user_penalty[['User_id', 'penalty_user_sum']], on='User_id')
    df = pd.merge(df, sites_penalty[['Site_id', 'penalty_site_sum']], on='Site_id')
    df = pd.merge(df, ip_penalty[['User_IP', 'penalty_ip_sum']], on='User_IP')

    df['penalty_all'] = df.penalty_user_sum + df.penalty_site_sum + df.penalty_ip_sum

    df['fraud'] = (df.penalty_all > np.percentile(df.penalty_all, 95)).astype(int)
    user_fraud = df.groupby('User_id')['fraud'].mean()

    user_to_send = user_penalty.loc[user_penalty.User_id.isin(user_fraud[user_fraud > 0.5].keys()), ]

    user_to_send = user_to_send.loc[user_to_send.n_user_clicks >= 3, ['User_id', 'n_user_clicks']]

    site_fraud = df.groupby('Site_id')['fraud'].mean()
    site_to_send = sites_penalty[sites_penalty.Site_id.isin(site_fraud[site_fraud > 0.3].keys())]
    site_to_send = site_to_send[['Site_id', 'n_sites_clck']]

    ip_fraud = df.groupby('User_IP')['fraud'].mean()
    ip_to_send = ip_penalty[ip_penalty.User_IP.isin(ip_fraud[ip_fraud >= 0.5].keys())]
    ip_to_send = ip_to_send[['User_IP', 'n_clks']]

    return {
        'users': user_to_send.to_json(orient='records'),
        'sites': site_to_send.to_json(orient='records'),
        'ips': ip_to_send.to_json(orient='records')
    }
