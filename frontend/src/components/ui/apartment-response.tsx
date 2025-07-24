"use client"

import { ApartmentCard } from "./apartment-card"
import {
    Carousel,
    CarouselContent,
    CarouselItem,
    CarouselNext,
    CarouselPrevious,
} from "./carousel"

interface Apartment {
    title: string
    price: string
    bedrooms: number
    bathrooms: number
    location: string
    imageUrl: string
}

interface ApartmentResponseProps {
    text: string
}

export function ApartmentResponse({ text }: ApartmentResponseProps) {
    // Fonction pour parser le texte et extraire les appartements
    const parseApartments = (text: string): { intro: string; apartments: Apartment[] } => {
        const apartments: Apartment[] = []
        let intro = ""

        // Extraire l'introduction (tout avant le premier numéro)
        const introMatch = text.match(/^([^*\n]+?)(?=\d+\.\s*\*\*)/s)
        if (introMatch) {
            intro = introMatch[1].trim()
        }

        // Regex pour trouver les appartements
        const apartmentRegex = /(\d+)\.\s*\*\*([^*]+)\*\*\s*((?:[^!]+?)(?=\d+\.\s*\*\*|$))/gs

        let match
        while ((match = apartmentRegex.exec(text)) !== null) {
            const apartmentText = match[3]

            // Extraire les informations
            const priceMatch = apartmentText.match(/\*\*Prix\*\*:\s*([^\n]+)/)
            const bedroomsMatch = apartmentText.match(/\*\*Chambres\*\*:\s*(\d+)/)
            const bathroomsMatch = apartmentText.match(/\*\*Salles de bain\*\*:\s*(\d+)/)
            const locationMatch = apartmentText.match(/\*\*Localisation\*\*:\s*([^\n]+)/)
            const imageMatch = apartmentText.match(/!\[Photo\]\(([^)]+)\)/)

            if (priceMatch && bedroomsMatch && bathroomsMatch && locationMatch) {
                apartments.push({
                    title: match[2].trim(),
                    price: priceMatch[1].trim(),
                    bedrooms: parseInt(bedroomsMatch[1]),
                    bathrooms: parseInt(bathroomsMatch[1]),
                    location: locationMatch[1].trim(),
                    imageUrl: imageMatch ? imageMatch[1] : ""
                })
            }
        }

        return { intro, apartments }
    }

    const { intro, apartments } = parseApartments(text)

    if (apartments.length === 0) {
        // Si ce n'est pas une réponse d'appartements, afficher le texte normal
        return (
            <div className="whitespace-pre-wrap break-words">
                {text}
            </div>
        )
    }

    return (
        <div className="space-y-4">
            {/* Introduction */}
            {intro && (
                <div className="text-gray-700 mb-4">
                    {intro}
                </div>
            )}

            {/* Carousel d'appartements */}
            <div className="relative">
                <Carousel
                    opts={{
                        align: "start",
                        loop: false,
                    }}
                    className="w-full"
                >
                    <CarouselContent className="-ml-2 md:-ml-4">
                        {apartments.map((apartment, index) => (
                            <CarouselItem key={index} className="pl-2 md:pl-4 basis-full md:basis-1/2 lg:basis-1/3">
                                <ApartmentCard
                                    title={apartment.title}
                                    price={apartment.price}
                                    bedrooms={apartment.bedrooms}
                                    bathrooms={apartment.bathrooms}
                                    location={apartment.location}
                                    imageUrl={apartment.imageUrl}
                                />
                            </CarouselItem>
                        ))}
                    </CarouselContent>

                    {apartments.length > 1 && (
                        <>
                            <CarouselPrevious className="left-2 md:left-4" />
                            <CarouselNext className="right-2 md:right-4" />
                        </>
                    )}
                </Carousel>
            </div>

            {/* Message de fin */}
            <div className="text-gray-600 text-sm mt-4">
                Si vous souhaitez plus d&apos;informations sur l&apos;un de ces appartements ou d&apos;autres options, n&apos;hésitez pas à demander !
            </div>
        </div>
    )
} 