import os
import json
import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv, find_dotenv
import deepl

from bundestag.config import language_codes


load_dotenv(find_dotenv(), override=True)
logger = logging.getLogger(__name__)
dashapp_rootdir = Path(__file__).resolve().parents[2]

# make the dictionary available to the whole app, so not each and every
# string that gets translated at app init triggers loading the json data:
dictionary_path = dashapp_rootdir / "i18n" / "dictionary.json"
multiling_dictionary = json.loads(dictionary_path.read_text())


def get_translations(labels: pd.Series, language: str) -> None:
    """
    Check voting labels for presence of their 'tgt_lang' translation in our
    dictionary, and if missing, translate them and store them right there.
    This only ensures presence; for the function that returns translations,
    see => translate_labels().
    """
    # load label dictionary and set to target language:
    dictionary_path = dashapp_rootdir / "i18n" / "dictionary.json"
    global_dictionary = json.loads(dictionary_path.read_text())
    src = language_codes["de"]
    tgt = language_codes[language]
    logger.info(f"Global dict has {len(global_dictionary)} entries.")

    dict_de = bilingualize_dict(src=src, tgt=language)

    # identify new labels (not in dict or not in the desired language):
    data_labels = labels.unique()
    new_labels = [
        label
        for label in data_labels
        if label not in dict_de or dict_de.get(label, {}).get(tgt, None) is None
    ]

    # do the translating and put it into the global dictionary:
    if new_labels:
        auth_key = os.getenv("DEEPL_AUTH_KEY", None)
        if auth_key:
            logger.info(f"Translating {len(new_labels)} new labels.")
            translator = deepl.Translator(auth_key)
            # new_entries: {"lorem": "ipsum", ...}
            new_entries = {
                key: translator.translate_text(
                    key, target_lang=tgt, source_lang=src
                ).text
                for key in new_labels
            }

            # bring new entries into the focused dict_de
            for k, v in new_entries.items():
                if k in dict_de:
                    # entry exisits, but add this new language:
                    dict_de[k][tgt] = v
                else:
                    # add completely new entry:
                    dict_de[k] = {tgt: v}

            # bring the focused dict_de into the international form:
            global_dictionary = _defocus_dict(dict_de, src=src)

            logger.info(f"Adding {len(new_entries)} new entries to the dictionary.")
            json.dump(
                global_dictionary,
                open(dictionary_path, "w"),
                indent=4,
                ensure_ascii=False,
            )

        else:
            logger.warning("No DeepL key found. Translations will not be available.")
    else:
        logger.info("No new labels found. No translation needed.")


def bilingualize_dict(src: str = "de", tgt: str = "de") -> dict:
    """
    Take the global dictionary, and return a simple bilingual dictionary.
    Go from
      [ {"DE": "lorem", "EN": "ipsum"}, ... ]
    to
      {"lorem": "ipsum", ...}

    :param global_dict: the dictionary to focus
    :param src: the focal language
    :param tgt: the target language
    :return: the bilingual dictionary
    """
    global multiling_dictionary

    src = language_codes[src]
    tgt = language_codes[tgt]

    biling_dictionary = {
        str(entry[src]): str(entry[tgt])
        for entry in multiling_dictionary
        if src in entry and tgt in entry
    }

    return biling_dictionary

biling_dictionary = bilingualize_dict()


def _defocus_dict(focused_dict: dict, src: str) -> dict:
    """
    Take a focused dictionary, and return a global dictionary. Go from form
    > {"lorem": {"EN": "ipsum"}, ...}

    to

    > [ {"DE": "lorem", "EN": "ipsum"}, ... ]

    This is the inverse of _focus_dict().

    :param focused_dict: the dictionary to unfocus
    :param src: the focal language, i.e., the language of the keys
    :return: the global dictionary
    """
    multiling_dict = []
    for k, v in focused_dict.items():
        entry = {src: k}
        entry.update(v)
        multiling_dict.append(entry)

    return multiling_dict


def translate_labels(labels: pd.Series, tgt_lang: str = "en") -> pd.Series:
    """
    Specialization of cached_translation() for the specific use case of a
    pd.Series.

    :param labels: pd.Series of string labels to translate.
    :param tgt_lang: the target language. Uses our app codes, "de", "en", etc.
    :return: the translated labels, as pd.Series
    """
    global biling_dictionary

    if tgt_lang == "de":
        return labels

    labels = labels.replace(biling_dictionary)

    return labels


def translate(text: str, tgt_lang: str = "de") -> str:
    """
    Return a previously-cached translation for the given German string. If the
    current language is "de", just return the input string unchanged. Else,
    if no translation is found, [TODO] get it from DeepL and store it in both
    the bilingual and multilingual dictionaries.

    :param text: the string to translate
    :param src_lang: the source language. Uses our app codes, "de", "en", etc.
    :param tgt_lang: the target language. Uses our app codes, "de", "en", etc.
    :return: the translated string
    """
    if tgt_lang == "de":
        return text

    if text is None:
        return None

    global biling_dictionary

    translated_text = biling_dictionary.get(text)

    if translated_text is None:
        logger.error(f"No translation found for '{text[0:30]}' in {tgt_lang}.")
        return text

    return translated_text
