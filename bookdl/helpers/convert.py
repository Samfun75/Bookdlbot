import time
import asyncio
import logging
import aiohttp
import aiofiles
import convertapi
from pathlib import Path
import humanfriendly as size
from bookdl.helpers import Util
from bookdl.common import Common
from pyrogram.types import Message
from convertapi.exceptions import ApiError
from libgenesis.download import LibgenDownload
from bookdl.helpers.uploader import Uploader
from pyrogram.errors import MessageNotModified, FloodWait

logger = logging.getLogger(__name__)
convert_status = {}


class Convert:
    def __init__(self):
        convertapi.api_secret = Common().convert_api

    async def convert_to_pdf(self, md5: str, msg: Message):
        ack_msg = await msg.reply_text('About to convert book to PDF...',
                                       quote=True)

        _, detail = await Util().get_detail(
            md5, return_fields=['mirrors', 'title', 'extension'])

        temp_dir = Path.joinpath(
            Common().working_dir,
            Path(f'{ack_msg.chat.id}+{ack_msg.message_id}'))
        if not Path.is_dir(temp_dir):
            Path.mkdir(temp_dir)
        file_path = Path.joinpath(
            temp_dir, Path(detail['title'] + '  [@SamfunBookdlbot]' + '.pdf'))

        direct_links = await LibgenDownload().get_directlink(
            detail['mirrors']['main'])
        extension = detail['extension']
        params = {
            'File': direct_links[1],
            'FileName': detail['title'],
            'PdfVersion': '2.0',
            'OpenZoom': '100',
            'PdfTitle': '@SamfunBookdlbot - ' + detail['title'],
            'RotatePage': 'ByPage'
        }
        stat_var = f"{ack_msg.chat.id}{ack_msg.message_id}"
        convert_status[stat_var] = {'Done': False}
        try:
            loop = asyncio.get_event_loop()
            convert_process = loop.run_in_executor(None, self.__convert,
                                                   params, extension, stat_var)
        except ApiError as e:
            logger.error(e)
            await ack_msg.edit_text(e)
        start_time = time.time()
        while True:
            if convert_status[stat_var]['Done']:
                break
            else:
                try:
                    await ack_msg.edit_text(
                        f'Convertion to PDF started... {int(time.time() - start_time)}'
                    )
                except MessageNotModified as e:
                    logger.error(e)
                except FloodWait as e:
                    logger.error(e)
                    await asyncio.sleep(e.x)
                await asyncio.sleep(2)
        Result = await convert_process
        await ack_msg.reply_text(
            f'Conversion Costed **{Result.conversion_cost}** seconds from ConvertAPI.'
        )
        await ack_msg.edit_text(f'About to download converted file...')
        try:
            async with aiohttp.ClientSession() as dl_ses:
                async with dl_ses.get(Result.file.url) as resp:
                    total_size = int(Result.file.size)
                    file_name = Result.file.filename

                    async with aiofiles.open(file_path, mode="wb") as dl_file:
                        current = 0
                        logger.info(f'Starting download: {file_name}')
                        async for chunk in resp.content.iter_chunked(1024 *
                                                                     1024):
                            await dl_file.write(chunk)
                            current += len(chunk)
                            await ack_msg.edit_text(
                                f'Downloading: **{detail["title"]}**\n'
                                f"Status: **{size.format_size(current, binary=True)}** of **{size.format_size(total_size, binary=True)}**"
                            )
        except Exception as e:
            logger.exception(e)
            return None
        await Uploader().upload_book(file_path, ack_msg, md5)

    @staticmethod
    def __convert(params, extension, stat_var):
        convertapi.api_secret = Common().convert_api
        logger.info('Conversion Started...')
        result = convertapi.convert('pdf',
                                    params,
                                    from_format=extension,
                                    timeout=120)
        logger.info('Conversion Finished!')
        convert_status[stat_var]['Done'] = True
        return result