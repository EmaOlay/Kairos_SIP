"""
Tests unitarios para kairos.utils.config_loader

Aca chequeamos que el cargador de configuracion no se haga el vivo y levante
bien los archivos JSON. Si no encuentra el archivo, tiene que chillar.
"""

import pytest
import json
from pathlib import Path
from kairos.utils.config_loader import ConfigLoader


class TestConfigLoader:
    """
    Suite de tests para el ConfigLoader.
    
    Es fundamental que levante bien los parametros de optimizacion y demas yerbas.
    """

    @pytest.fixture
    def config_file_valido(self, tmp_path):
        """Fixture que genera un archivo de configuracion valido para probar"""
        config_data = {
            "kairos": {
                "version": "1.0.0",
                "entorno": "test"
            },
            "optimization": {
                "min_tasa_ocupacion": 0.6,
                "priorizar_graduacion": True
            }
        }
        ruta = tmp_path / "test_config.json"
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(config_data, f)
        return ruta

    def test_cargar_config_valida(self, config_file_valido):
        """
        Verifica que carga el diccionario completo sin vueltas.
        """
        config = ConfigLoader.cargar(config_file_valido)
        assert config["kairos"]["version"] == "1.0.0"
        assert config["optimization"]["min_tasa_ocupacion"] == 0.6

    def test_obtener_kairos_config(self, config_file_valido):
        """
        Chequea que traiga solo la parte de 'kairos'.
        """
        kairos_config = ConfigLoader.obtener_kairos_config(config_file_valido)
        assert kairos_config["version"] == "1.0.0"
        assert "optimization" not in kairos_config

    def test_obtener_optimization_config(self, config_file_valido):
        """
        Prueba que traiga solo la parte de 'optimization'.
        """
        opt_config = ConfigLoader.obtener_optimization_config(config_file_valido)
        assert opt_config["min_tasa_ocupacion"] == 0.6
        assert "kairos" not in opt_config

    def test_archivo_inexistente_lanza_error(self):
        """
        Si le pasas un archivo que no existe, tiene que tirar un FileNotFoundError.
        No vale hacerse el distraido.
        """
        ruta_falopa = Path("ruta/al/infinito.json")
        with pytest.raises(FileNotFoundError):
            ConfigLoader.cargar(ruta_falopa)
