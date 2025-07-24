"use client"

import { useState } from "react"
import { MapPin, Bed, Bath, Yen } from "lucide-react"

interface ApartmentCardProps {
    title: string
    price: string
    bedrooms: number
    bathrooms: number
    location: string
    imageUrl: string
}

export function ApartmentCard({
    title,
    price,
    bedrooms,
    bathrooms,
    location,
    imageUrl
}: ApartmentCardProps) {
    const [imageError, setImageError] = useState(false)

    return (
        <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200 hover:shadow-xl transition-shadow duration-300">
            {/* Image */}
            <div className="relative h-48 bg-gray-100">
                {!imageError ? (
                    <img
                        src={imageUrl}
                        alt={title}
                        className="w-full h-full object-cover"
                        onError={() => setImageError(true)}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gray-200">
                        <div className="text-gray-400 text-center">
                            <MapPin className="w-8 h-8 mx-auto mb-2" />
                            <p className="text-sm">Image non disponible</p>
                        </div>
                    </div>
                )}

                {/* Price badge */}
                <div className="absolute top-3 right-3 bg-black text-white px-2 py-1 rounded-lg text-sm font-semibold">
                    {price}
                </div>
            </div>

            {/* Content */}
            <div className="p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>

                {/* Features */}
                <div className="flex items-center gap-4 mb-3 text-sm text-gray-600">
                    <div className="flex items-center gap-1">
                        <Bed className="w-4 h-4" />
                        <span>{bedrooms} chambre{bedrooms > 1 ? 's' : ''}</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Bath className="w-4 h-4" />
                        <span>{bathrooms} salle{bathrooms > 1 ? 's' : ''} de bain</span>
                    </div>
                </div>

                {/* Location */}
                <div className="flex items-start gap-2 text-sm text-gray-600">
                    <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span className="line-clamp-2">{location}</span>
                </div>
            </div>
        </div>
    )
} 