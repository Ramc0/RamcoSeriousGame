# RamcoSeriousGame
---

# 🗺 RamcoSeriousGame — Sistema Geoespacial Interactivo con Control Gestual

## 📌 Descripción general

**RamcoSeriousGame** es una aplicación web interactiva que integra visualización cartográfica y control gestual en tiempo real. El sistema permite interactuar con un mapa digital sin utilizar ratón ni teclado, aplicando gestos naturales detectados con cámara.

Combina:

* 🗺 **Leaflet + OpenStreetMap** para representación cartográfica
* ✋ **MediaPipe Hands** para reconocimiento de gestos
* 📏 Cálculo real de distancias geográficas
* 🧠 Gestión dinámica de estado y rutas

---

## 🎯 Objetivo del proyecto

El proyecto parte de un ejercicio base de interacción multimedia y lo amplía mediante:

* Modificaciones funcionales relevantes
* Mejora estructural del código
* Rediseño visual del interfaz
* Implementación de nuevas capacidades

Su finalidad es demostrar cómo las tecnologías utilizadas en videojuegos e interfaces gráficas pueden aplicarse a aplicaciones interactivas de carácter más profesional o empresarial.

---

## 🧠 Tecnologías utilizadas

* HTML5
* CSS3
* JavaScript
* Leaflet.js
* OpenStreetMap
* MediaPipe Hands
* API de cálculo de distancia geográfica de Leaflet

---

## 🖐 Sistema de interacción gestual

| Gesto                      | Acción                               |
| -------------------------- | ------------------------------------ |
| ✊ Puño mantenido 1 segundo | Crear marcador en el centro del mapa |
| 🤏 Pinza (pulgar + índice) | Arrastrar mapa                       |
| 🤏🤏 Dos manos en pinza    | Zoom progresivo                      |
| 👋 Mano abierta            | Estado neutro                        |

---

## 📍 Funcionalidades implementadas

### 1️⃣ Creación dinámica de marcadores

Los marcadores se crean en el centro exacto del mapa, indicado mediante un punto de mira visual.

### 2️⃣ Punto de referencia central

Se ha añadido un indicador visual fijo que muestra con precisión dónde se colocará el siguiente marcador.

### 3️⃣ Generación automática de rutas

Cada nuevo marcador se conecta con el anterior mediante una línea (polyline), generando una ruta visual progresiva.

### 4️⃣ Cálculo real de distancias

Se calcula la distancia geográfica real entre marcadores consecutivos utilizando:

```
map.distance(latlng1, latlng2)
```

El sistema:

* Calcula distancia parcial entre puntos
* Acumula distancia total recorrida
* Muestra valores en kilómetros con dos decimales

### 5️⃣ Dashboard lateral

Interfaz mejorada que incluye:

* Contador dinámico de marcadores
* Distancia total acumulada
* Botón para limpiar marcadores y rutas
* Guía visual de gestos

---

## 🗂 Estructura del proyecto

```
RamcoSeriousGame/
│
├── RamcoSeriousGame.html
└── README.md
```

Todo el sistema está implementado en un único archivo HTML que integra estructura, estilos y lógica.

---

## ▶️ Ejecución

1. Clonar el repositorio:
2. Abrir `RamcoSeriousGame.html` en un navegador (Chrome recomendado).
3. Permitir acceso a la cámara cuando el navegador lo solicite.

No requiere backend ni instalación adicional.

---

## 🧩 Arquitectura del sistema

El proyecto se organiza en tres bloques principales:

### 🔹 Visualización

Leaflet gestiona el mapa, los marcadores y las rutas.

### 🔹 Detección gestual

MediaPipe analiza los landmarks de la mano en tiempo real para detectar gestos específicos.

### 🔹 Lógica de aplicación

Se gestionan:

* Estados (zoom, drag, creación)
* Arrays de marcadores y rutas
* Cálculo acumulado de distancias
* Actualización dinámica del interfaz

---

## 🎓 Enfoque académico

Este proyecto forma parte del módulo de Programación Multimedia y responde a los criterios de evaluación centrados en:

* Modificaciones estéticas significativas
* Modificaciones funcionales de calado
* Mejora estructural del código base
* Integración efectiva de tecnologías vistas en clase

---

## 🚀 Posibles mejoras futuras

* Integración con API de rutas reales
* Guardado persistente de recorridos
* Exportación en formato JSON
* Personalización avanzada de marcadores
* Sistema de medición libre por puntos

---

## 👨‍💻 Autoría

Proyecto desarrollado como trabajo académico dentro del módulo de Programación Multimedia.
