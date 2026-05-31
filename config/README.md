# Configuracion de Kairos

## Archivos de Configuracion

Las configuraciones se almacenan en archivos JSON en esta carpeta.

### kairos_config.json

Define los parametros operacionales del motor de optimizacion:

#### Seccion 'kairos'
Parametros del motor:
- `min_tasa_ocupacion`: Ocupacion minima para abrir una comision (0.0-1.0). Default: 0.6
- `max_cupos_por_comision`: Maximo de estudiantes por comision. Default: 50
- `weight_tasa_graduacion`: Peso relativo de tasa de graduacion en optimizacion (0.0-1.0). Default: 0.7
- `weight_eficiencia_operativa`: Peso relativo de costos operativos (0.0-1.0). Default: 0.3
- `anos_estudio`: Duracion total de la carrera en anos. Default: 5
- `cuatrimestres_por_ano`: Cuatrimestres por ano academico. Default: 2

#### Seccion 'optimization'
Parametros de optimizacion avanzada:
- `threshold_demanda_minima`: Minimo de estudiantes demandando una materia. Default: 3
- `penalizacion_costo_operativo`: Factor de penalizacion por costos. Default: 100

## Cargar configuracion desde Python

```python
from kairos.utils import ConfigLoader
from kairos.schemas.data_models import ConfiguracionKairos

# Cargar seccion 'kairos'
config_dict = ConfigLoader.obtener_kairos_config()
config = ConfiguracionKairos(**config_dict)

# Cargar seccion 'optimization'
opt_config = ConfigLoader.obtener_optimization_config()
```

## Entornos (futuro)

Configuraciones por entorno proximamente en:
- `kairos_config.development.json`
- `kairos_config.testing.json`
- `kairos_config.production.json`

## Variables de Entorno

Proximamente sera posible sobrescribir valores via variables de entorno:

```bash
export KAIROS_ENV=development
export KAIROS_MIN_TASA_OCUPACION=0.5
export KAIROS_MAX_CUPOS=40
```

Crear archivo `.env.local` con tus valores locales.
