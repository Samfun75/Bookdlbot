import re
import asyncio
import logging
from typing import Tuple
from libgenesis import Libgen
from libgenesis.utils import Util as libgenUtil
import humanfriendly as size

logger = logging.getLogger(__name__)


class Util:
    @staticmethod
    async def get_md5(link: str) -> str:
        regex_md5 = re.compile(
            r'(?<=/main/)([\w-]+)|(?<=md5=)([\w-]+)|(?<=/md5/)([\w-]+)')
        match = re.search(regex_md5, link)
        if match is not None:
            for md5 in match.groups():
                if md5 is not None:
                    return md5
        return None

    @staticmethod
    async def get_detail(md5: str,
                         return_fields: list = [],
                         retry: int = 0) -> Tuple[str, dict]:
        try:
            result = await Libgen().search(
                query=md5,
                search_field='md5',
                return_fields=[
                    'title', 'author', 'publisher', 'year', 'language',
                    'volumeinfo', 'filesize', 'extension', 'timeadded',
                    'timelastmodified', 'coverurl'
                ] if not return_fields else return_fields)
            book_id = list(result.keys())[0]
            return book_id, result[book_id]
        except ConnectionError as e:
            if str(e).find('max_user_connections') != -1 and retry <= 3:
                logger.info(f'Retry {retry + 1}')
                await asyncio.sleep(2)
                return await Util().get_detail(md5,
                                               return_fields,
                                               retry=retry + 1)
            else:
                await libgenUtil.raise_error(500, str(e))

    @staticmethod
    async def get_formatted(detail: dict) -> str:
        formated = ''
        formated += 'Title: **' + str(detail['title']) + '**\n'
        formated += 'Author: **' + str(detail['author']) + '**\n'
        formated += 'Volume: **' + str(detail['volumeinfo']) + '**\n'
        formated += 'Publisher: **' + str(detail['publisher']) + '**\n'
        formated += 'Year: **' + str(detail['year']) + '**\n'
        formated += 'Language: **' + str(detail['language']) + '**\n'
        formated += f"Size: **{size.format_size(int(detail['filesize']), binary=True)}**\n"
        formated += 'Extention: **' + str(detail['extension']) + '**\n'
        formated += 'Added Time: **' + str(detail['timeadded']) + '**\n'
        formated += 'Last Modified Time: **' + \
            str(detail['timelastmodified']) + '**\n'
        return formated
