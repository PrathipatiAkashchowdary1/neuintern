import { FiStar } from 'react-icons/fi'

export default function ReviewCard({ review }) {
  return (
    <div className="glass rounded-3xl p-7 h-full flex flex-col">
      <div className="flex gap-1 text-spark-500">
        {Array.from({ length: 5 }).map((_, i) => (
          <FiStar key={i} size={16} fill={i < review.rating ? 'currentColor' : 'none'} />
        ))}
      </div>
      <p className="text-ink-800 mt-4 leading-relaxed flex-1">&ldquo;{review.review}&rdquo;</p>
      <div className="flex items-center gap-3 mt-6">
        <img
          src={review.photo}
          alt={review.name}
          className="w-11 h-11 rounded-full object-cover"
          loading="lazy"
          width={44}
          height={44}
        />
        <div>
          <p className="font-semibold text-sm text-ink-900">{review.name}</p>
          <p className="text-xs text-ink-400">
            {review.college} · {review.program}
          </p>
        </div>
      </div>
    </div>
  )
}
