# -*- coding: utf-8 -*-

import requests
import numpy as np
import pandas as pd
import bs4
from bs4 import BeautifulSoup
import unicodedata
import json

"""## parsing costs"""

def parse_costs(which="fees", link="https://admissions.hse.ru/en/graduate-apply/fees"):
    """
    Returns a table with (name, cost)
    
    :which: either "fees" or "living", meaning either programme tuition fees or living costs respectively
    :link: base link for the page, where the info is located
    """
    # getting the page code
    r = requests.get(link)
    s = BeautifulSoup(r.text, "html.parser")

    if which == "fees":
        idx = 0
    elif which == "living":
        idx = -1
    else:
        raise Exception('Unknown value for "which" argument specified!')

    def parse_table(idx=0):
        # Looping through the tags to extract raw data
        lst = []
        for i in range(len(s.find_all(name="table")[idx].find("tbody").find_all("td"))):
            val = (
                s.find_all(name="table")[idx].find("tbody").find_all("td")[i].text.strip()
            )
            if (
                not (i % 2 == 0 and val == "") and val != "Language Programmes"
            ):  # there are some gaps
                lst.append((i, val))

        # there is a sequence of format ...name, cost, name, cost...
        # formatting it:
        dd = {lst[i][-1]: lst[i + 1][-1] for i in range(len(lst) - 1) if i % 2 == 0}
        d = {}
        for k, v in dd.items():
            if "RUB" in k or "USD" in k or "request" in k:
                d[v] = k
            else:
                d[k] = v

        df = pd.DataFrame(d, index=[0]).T.reset_index()
        df.columns = ["Programme", "Tuition (per year)"]
        return df

    df = parse_table(idx=idx)
    return df



"""## parsing rankings"""

def parse_rankings(link="https://strategy.hse.ru/en/rating/"):
    """
    Returns a table with ['ranking', 'subject', 'place_world', 'place_russia']

    :link: base link for the page, where the info is located
    """

    r = requests.get(link)
    s = BeautifulSoup(r.text, "html.parser")

    lst = []
    for i, tr in enumerate(
        s.find(name="table", attrs={"class": "data rate_top smaller"})
        .find("tbody")
        .find_all("tr")
    ):

        # link to the ranking
        try:
            a = tr.find("a").text
        except (TypeError, AttributeError):
            a = None

        tds = tr.find_all("td")
        len_tds = len(tds)
        try:
            if len_tds == 3:  # there's only subject, no ranking name
                # name aka subject
                name = tds[0].text.strip()
                # HSE in the World/Europe
                europe = tds[1].text.strip()
                # HSE in the World/Europe
                russia = tds[2].text.strip()
            elif len_tds == 4:  # there're both ranking name & subject
                # removing symbols like '\xa0'
                tds = [
                    unicodedata.normalize("NFKD", el.text).strip()
                    for el in tr.find_all("td")
                ]
                # name aka subject
                a = tds[0]
                name = tds[1]
                # HSE in the World/Europe
                europe = tds[2]
                # HSE in the World/Europe
                russia = tds[3]
        except (IndexError, TypeError):
            name = None
            europe = None
            russia = None

        lst.append((a, name, europe, russia))

    df = pd.DataFrame(lst)
    df.columns = ["ranking", "subject", "place_world", "place_russia"]
    df["subject"] = df.apply(
        lambda row: row["subject"] if row["ranking"] != row["subject"] else None, axis=1
    )
    df["ranking"].ffill(
        inplace=True
    )  # filling the ranking name values for all subjects
    return df.drop_duplicates()


"""## parsing programmes"""

def parse_programmes(link="https://www.hse.ru/en/education/magister/"):
    """
    Returns a table with Bachelor & Masters programmes.
    """

    r = requests.get(link)
    s = BeautifulSoup(r.text, "html.parser")

    d = []
    main_div = s.find('div', {'id': "education-programs__list"})
    for i, div_group in enumerate(
        main_div.find_all("div", attrs={"class": "edu-programm__group"})
    ):
        locations = [
            list(el.children)[0].text
            for el in div_group.find_all("div", {"class": "edu-programm__unit"})
            if type(list(el.children)[0]) == bs4.element.Tag # there're some None's
        ]
        for j, div in enumerate(
            div_group.find_all("div", {"class": "b-row edu-programm__item"})
        ):
            try:
                div_unit = div.find("div", {"class": "edu-programm__unit"})
                programme = div_group.find("h3").text
                link = div_group.find("a", {"class": "link"})["href"]
                if "/ba/" in link:
                    type_ = "bachelors"
                elif "/ma/" in link or "mag-" in link:
                    type_ = "masters"
                else:
                    type_ = "unknown"
                d.append(
                    {
                        "programme": programme,
                        "faculty": div.find("a", {"class": "link"}).text,
                        "link": link,
                        "type": type_,
                        "department": div.find("span", {"class": "grey"}).text,
                        "location": locations[j],
                        "duration": div.find(
                            "div", {"class": "edu-programm__data u-accent"}
                        ).text,
                        "schedule": div.find(
                            "div", {"class": "edu-programm__edu_offline"}
                        ).text,
                        "language": div.find(
                            "div",
                            {
                                "class": "b-row__item b-row__item--4 b-row__item--t8 b-row__item--places"
                            },
                        ).text,
                    }
                )
            except Exception as e:
                print("EXCEPTION: ", e)
                pass
    df = pd.DataFrame(d)
    return df


"""## parsing housing FAQ"""

def parse_housing_faq(link="https://www.hse.ru/en/sho/"):
    """
    Returns the FAQ table from https://www.hse.ru/en/sho/
    """

    r = requests.get(link)
    s = BeautifulSoup(r.text, "html.parser")

    # the block where all the data is held
    faq_block = s.find_all(
        "div", {"class": "builder-section builder-section--bottom0"}
    )[1]
    questions = [
        el.text for el in faq_block.find_all("h3", {"class": "foldable_control"})
    ]
    # unflattened list with answers
    ans_grouped = [
        el.find_all("p")
        for el in faq_block.find_all("div", {"class": "incut foldable_block__item"})
    ]

    # flattening the list with answers
    answers = []
    for group in ans_grouped:
        texts = [el.text for el in group]
        answers.append("\n".join(texts))

    d = dict(zip(questions, answers))

    df = pd.DataFrame(d, index=[0]).T.reset_index()
    df.columns = ["question", "answer"]

    return df

