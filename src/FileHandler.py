from pathlib import Path
import pandas as pd

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
    
