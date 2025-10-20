declare module "three/examples/jsm/controls/OrbitControls" {
  import { Camera, EventDispatcher, MOUSE, TOUCH, Vector3 } from "three"

  export class OrbitControls extends EventDispatcher {
    constructor(camera: Camera, domElement?: HTMLElement)
    camera: Camera
    domElement: HTMLElement
    target: Vector3
    enableDamping: boolean
    dampingFactor: number
    enableZoom: boolean
    zoomSpeed: number
    enableRotate: boolean
    rotateSpeed: number
    enablePan: boolean
    panSpeed: number
    autoRotate: boolean
    autoRotateSpeed: number
    minDistance: number
    maxDistance: number
    minZoom: number
    maxZoom: number
    minPolarAngle: number
    maxPolarAngle: number
    minAzimuthAngle: number
    maxAzimuthAngle: number
    enableKeys: boolean
    keys: { LEFT: number; UP: number; RIGHT: number; BOTTOM: number }
    mouseButtons: { LEFT: MOUSE; MIDDLE: MOUSE; RIGHT: MOUSE }
    touches: { ONE: TOUCH; TWO: TOUCH }
    dispose(): void
    reset(): void
    update(): void
    saveState(): void
    getPolarAngle(): number
    getAzimuthalAngle(): number
  }
}
