import io
import unittest

from werkzeug.datastructures import FileStorage

from app.routes_contas import _parse_csv_rows, _validate_import_row


class ContasCsvTestCase(unittest.TestCase):
    def test_parse_csv_rows_accepts_semicolon_and_trims_columns(self):
        payload = (
            " codigo ; nome ; tipo ; natureza ; parent_codigo \n"
            "1;Ativo;Ativo;Devedora;\n"
            "1.1;Caixa;Ativo;Devedora;1\n"
        ).encode('utf-8')
        file_storage = FileStorage(stream=io.BytesIO(payload), filename='plano.csv')

        rows = _parse_csv_rows(file_storage)

        self.assertEqual(2, len(rows))
        self.assertEqual('1', rows[0]['codigo'])
        self.assertEqual('1', rows[1]['parent_codigo'])

    def test_validate_import_row_ignores_existing_codigo(self):
        row = {
            'codigo': '1.1',
            'nome': 'Caixa',
            'tipo': 'Ativo',
            'natureza': 'Devedora',
            'parent_codigo': '1',
        }

        is_valid, message, parent_codigo = _validate_import_row(row, {'1.1'}, set())

        self.assertIsNone(is_valid)
        self.assertIn('Codigo ja existente', message)
        self.assertEqual('1', parent_codigo)


if __name__ == '__main__':
    unittest.main()
