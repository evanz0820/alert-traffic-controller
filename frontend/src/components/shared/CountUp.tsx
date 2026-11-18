import { animate, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'

/** Animates from the previously shown value to the new one when data changes. */
export function CountUp({
  value,
  format,
  className,
}: {
  value: number
  format: (n: number) => string
  className?: string
}) {
  const ref = useRef<HTMLSpanElement>(null)
  const previous = useRef(0)
  const reduce = useReducedMotion()
  const [initial] = useState(() => format(reduce ? value : 0))

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (reduce) {
      node.textContent = format(value)
      previous.current = value
      return
    }
    const controls = animate(previous.current, value, {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        node.textContent = format(v)
      },
    })
    previous.current = value
    return () => controls.stop()
  }, [value, format, reduce])

  return (
    <span ref={ref} className={className}>
      {initial}
    </span>
  )
}
