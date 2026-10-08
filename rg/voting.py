# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json
from collections.abc import MutableSequence
from contextlib import suppress
from typing import Literal, TypedDict

from rg.defs import SITE_AJAX_REQUEST_VIDEO_VOTING
from rg.fetch_html import fetch_html_raw
from rg.logger import Log
from rg.tagger import get_artist_num, get_category_num, get_tag_num


class ACTVoting(TypedDict):
    status: Literal['normal', 'hardened', 'unk_pending', 'unk_removed']
    user_vote: int  # bool?
    progress: int  # 0-100?
    pressure: Literal['up', 'down', '']


class TagVoting(ACTVoting):
    tag_id: int


class ArtCatVoting(ACTVoting):
    item_type: Literal['category', 'model']
    item_id: int


class PostVotings(TypedDict):
    status: Literal['success', 'unk_failure']
    video_id: int
    logged_in: int  # bool
    can_vote: int  # bool
    tags: list[TagVoting]
    items: list[ArtCatVoting]
    pending_tags: list
    pending_items: list


async def filter_act_by_votes_count(vi, ars: MutableSequence[str], cas: MutableSequence[str], tas: MutableSequence[str]) -> None:
    nameids_arts, nameids_cats, nameids_tags = {}, {}, {}
    for c, m, d in zip(
        (ars, cas, tas),
        (get_artist_num, get_category_num, get_tag_num),
        (nameids_arts, nameids_cats, nameids_tags),
        strict=True,
    ):
        for act in c:
            if act_id := m(act):
                d[act_id] = act
    tids, cids, aids = tuple(','.join(_.keys()) for _ in (nameids_tags, nameids_cats, nameids_arts))
    v_bytes = await fetch_html_raw(SITE_AJAX_REQUEST_VIDEO_VOTING % (vi.id, tids, cids, aids))
    if v_bytes is None:
        Log.error(f'Error: failed to fetch votings html for {vi.sname}! Votings check skipped!')
        return
    votings_json: PostVotings = json.loads(v_bytes)
    voting_status = votings_json['status']
    if voting_status != 'success':
        Log.error(f'Error: votings status is \'{voting_status}\' for {vi.sname}! Votings check skipped!')
        return
    for tv in votings_json['tags']:
        tid = str(tv['tag_id'])
        tstatus = tv['status']
        tprogress = tv['progress']
        tpressure = tv['pressure']
        if tstatus not in ('normal', 'hardened') or (tprogress <= 0 and tpressure == 'down'):
            tname = nameids_tags.get(tid, 'Unknown')
            Log.warn(f'{vi.sname}: tag \'{tname}\' ({tid}) is \'{tstatus}\', {tprogress}%, going \'{tpressure}\'. Removing!')
            with suppress(KeyError):
                tas.remove(tname)
    for acv in votings_json['items']:
        acid = str(acv['item_id'])
        acstatus = acv['status']
        acprogress = acv['progress']
        acpressure = acv['pressure']
        if acstatus not in ('normal', 'hardened') or (acprogress <= 0 and acpressure == 'down'):
            actype = acv['item_type']
            acname = {'category': nameids_cats, 'model': nameids_arts}.get(actype, {}).get(acid, 'Unknown')
            acs = {'category': cas, 'model': ars}.get(actype, [])
            Log.warn(f'{vi.sname}: {actype} \'{acname}\' ({acid}) is \'{acstatus}\', {acprogress}%, going \'{acpressure}\'. Removing!')
            with suppress(KeyError):
                acs.remove(acname)

#
#
#########################################
