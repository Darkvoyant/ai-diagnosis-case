import shutil
from pathlib import Path
import zipfile
from urllib.parse import unquote
import pandas as pd
import requests

class FileHandler():

    @staticmethod
    def read_file(path_to_file: str) -> pd.DataFrame:
        """
        Функция считывания .csv файла по принятому пути. 
        Возвращает pandas dataframe.
        """
        file_path = Path(path_to_file)

        if file_path.suffix.lower() != ".csv":
            raise ValueError(f"Ожидался файл с расширением .csv, но получен: '{file_path.name}'")
        try:
            return pd.read_csv(path_to_file)

        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Файл не найден по указанному пути: '{file_path}'") from exc

        except Exception as e:
            raise IOError(f"Не удалось прочитать файл '{file_path}': {e}") from e

    @staticmethod
    def download_and_unpack_data(url: str, target_dir: str) -> None:
        """
        Скачивает и распаковывает данные в папку data/raw. 
        После распаковки удаляет все данные в data/raw кроме скачанных csv.
        Требует наличие requests.
        """

        save_dir_path = Path(target_dir)

        for csv_file in save_dir_path.glob("*.csv"):
            csv_file.unlink()  # удаляет файл
        
        try:
            # создание data/raw
            save_dir_path.mkdir(parents=True, exist_ok=True)

            # загрузка
            with requests.get(url, stream=True, timeout=30) as r:

                # raise_for_status will rise an exception if status_code is 4xx or 5xx
                r.raise_for_status()

                # имя архива забираем из заголовка
                content_disposition = r.headers.get('content-disposition')
                if content_disposition:
                    filename = unquote(content_disposition.split('filename=')[1].strip('"'))
                else:
                    filename = "downloaded_archive.zip"

                archive_path = save_dir_path / filename

                # скачиваем архив
                with archive_path.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # распаковка
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(save_dir_path)

            # имена всех вложенных архивов (у нас только 1)
            csv_files = list(save_dir_path.rglob('*.csv'))

            # если нет csv, значит что-то пошло не так
            if not csv_files:
                raise ValueError(".csv файлы после разархивации не обнаружены")

            return None

        except requests.exceptions.RequestException as exc:
            raise requests.exceptions.RequestException("Ошибка при скачивании файла") from exc

        except zipfile.BadZipFile as exc:
            raise zipfile.BadZipFile("Не удалось распаковать zip") from exc

        except Exception as e:
            raise Exception(f"Непредвиденная ошибка {e}") from e

        finally:
            # удалить всё кроме .csv файлов в папке data/raw
            for path in save_dir_path.rglob("*"):
                if path.is_file() and path.suffix != ".csv":
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)


