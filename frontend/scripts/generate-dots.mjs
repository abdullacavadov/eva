import { readFileSync, writeFileSync } from "node:fs"
import * as d3 from "d3"

const EARTH_DOT_STEP = 1.7
const inputPath = "./public/earth_globe.json"
const outputPath = "./public/earth_dots.json"

const data = JSON.parse(readFileSync(inputPath, "utf-8"))
const dots = []

for (let latitude = -90 + EARTH_DOT_STEP / 2; latitude < 90; latitude += EARTH_DOT_STEP) {
  const longitudeOffset =
    (Math.floor((latitude + 90) / EARTH_DOT_STEP) % 2) * (EARTH_DOT_STEP / 2)

  for (let longitude = -180 + longitudeOffset; longitude < 180; longitude += EARTH_DOT_STEP) {
    if (d3.geoContains(data, [longitude, latitude])) {
      dots.push([longitude, latitude])
    }
  }
}

writeFileSync(outputPath, JSON.stringify(dots))
console.log(`${dots.length} dot generated -> ${outputPath}`)
