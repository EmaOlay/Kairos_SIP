"""
Cargador de configuracion para Kairos

Lee configuraciones desde archivos JSON en la carpeta config/.
Permite sobrescribir valores via variables de entorno o parametros.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import os


class ConfigLoader:
    """Carga y gestiona configuraciones de Kairos"""
    
    _CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
    _CONFIG_FILE = _CONFIG_DIR / "kairos_config.json"
    
    @classmethod
    def cargar(cls, config_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Carga configuracion desde JSON.
        
        Args:
            config_file: Ruta alternativa del archivo de config (default: config/kairos_config.json)
            
        Returns:
            Dict con la configuracion cargada
        """
        ruta = config_file or cls._CONFIG_FILE
        
        if not ruta.exists():
            raise FileNotFoundError(f"Archivo de config no encontrado: {ruta}")
        
        with open(ruta, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        return config
    
    @classmethod
    def obtener_kairos_config(cls, config_file: Optional[Path] = None) -> Dict[str, Any]:
        """Retorna solo la seccion 'kairos' de la configuracion"""
        config = cls.cargar(config_file)
        return config.get("kairos", {})
    
    @classmethod
    def obtener_optimization_config(cls, config_file: Optional[Path] = None) -> Dict[str, Any]:
        """Retorna solo la seccion 'optimization' de la configuracion"""
        config = cls.cargar(config_file)
        return config.get("optimization", {})
