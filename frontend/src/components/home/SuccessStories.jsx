import { Swiper, SwiperSlide } from 'swiper/react'
import { Autoplay, Pagination } from 'swiper/modules'
import ReviewCard from '../common/ReviewCard'
import { testimonials } from '../../data/testimonials'
import 'swiper/css'
import 'swiper/css/pagination'

export default function SuccessStories() {
  return (
    <section className="section-pad bg-cloud-200">
      <div className="container-page">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="eyebrow">Student Success Stories</span>
          <h2 className="text-3xl sm:text-4xl font-bold mt-3">Don&apos;t take our word for it</h2>
        </div>
        <Swiper
          modules={[Autoplay, Pagination]}
          spaceBetween={24}
          slidesPerView={1}
          autoplay={{ delay: 5000, disableOnInteraction: false }}
          pagination={{ clickable: true }}
          breakpoints={{
            640: { slidesPerView: 2 },
            1024: { slidesPerView: 3 },
          }}
          className="!pb-12"
        >
          {testimonials.map((review) => (
            <SwiperSlide key={review.id} className="h-auto pb-2">
              <ReviewCard review={review} />
            </SwiperSlide>
          ))}
        </Swiper>
      </div>
    </section>
  )
}
