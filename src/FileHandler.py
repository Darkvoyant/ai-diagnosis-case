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
    def download_data(url: str = 'https://drive.fondsmena.ru/s/3fiHapYG8cpbafk/download',
                      save_dir: str = './data/raw/') -> None:
        """
        Скачивает и распаковывает данные в папку data/raw. 
        После распаковки удаляет скачанный архив. 
        Требует наличие requests.
        """

        save_dir_path = Path(save_dir)
        # список путей для очистки в дальнейшем
        cleanup_paths = []

        try:

            # создание data/raw
            save_dir_path.mkdir(parents=True, exist_ok=True)

            # загрузка
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()

                # имя архива забираем из заголовка
                content_disposition = r.headers.get('content-disposition')
                if content_disposition:
                    filename = unquote(content_disposition.split('filename=')[1].strip('"'))
                else:
                    filename = "downloaded_archive.zip"

                first_archive_path = save_dir_path / filename
                cleanup_paths.append(first_archive_path)

                # скачиваем архив
                with first_archive_path.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # распаковка
            with zipfile.ZipFile(first_archive_path, 'r') as zip_ref:
                zip_ref.extractall(save_dir_path)

            # имена всех вложенных архивов (у нас только 1)
            nested_archives = [p for p in save_dir_path.rglob('*.zip') if p != first_archive_path]

            # если вложенных архивов нет, значит что-то пошло не так
            if not nested_archives:
                raise ValueError("Нет вложенного архива, который должен был быть")

            second_archive_path = nested_archives[0]
            second_archive_dir = second_archive_path.parent
            cleanup_paths.append(second_archive_path)

            with zipfile.ZipFile(second_archive_path, 'r') as zip_ref:
                zip_ref.extractall(save_dir_path)

            return None

        except requests.exceptions.RequestException as exc:
            raise requests.exceptions.RequestException("Ошибка при скачивании файла") from exc

        except zipfile.BadZipFile as exc:
            raise zipfile.BadZipFile("Не удалось распаковать zip") from exc

        except Exception as e:
            raise Exception(f"Непредвиденная ошибка {e}") from e

        finally:
            # удаляем все ненужные файлы и папки
            for path in cleanup_paths:
                if path.exists():
                    if path.is_file():
                        path.unlink()
            if second_archive_dir.exists() and second_archive_dir.is_dir():
                second_archive_dir.rmdir()


