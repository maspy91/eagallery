import type {
	GalleryItem,
	CommentNode,
	BusinessConversation,
	AppNotification,
	AppUser,
	Testimonial
} from '$lib/types';

import gallery1 from '$lib/assets/gallery-1.jpg';
import gallery2 from '$lib/assets/gallery-2.jpg';
import gallery3 from '$lib/assets/gallery-3.jpg';
import gallery4 from '$lib/assets/gallery-4.jpg';
import gallery5 from '$lib/assets/gallery-5.jpg';
import gallery6 from '$lib/assets/gallery-6.jpg';
export { default as heroBanner } from '$lib/assets/hero-banner.jpg';

export const galleryItems: GalleryItem[] = [
	{
		id: '1',
		image: gallery1,
		title: 'SmartWatch Pro',
		category: 'Wearable Tech',
		viewCount: 12453,
		likeCount: 892,
		description:
			'Next-generation smartwatch with advanced health monitoring and seamless connectivity.',
		specs: ['AMOLED Display', '5-Day Battery', 'Water Resistant', 'ECG Monitor'],
		status: 'published'
	},
	{
		id: '2',
		image: gallery2,
		title: 'AirPods Ultra',
		category: 'Audio',
		viewCount: 8721,
		likeCount: 654,
		description: 'Premium wireless earbuds with spatial audio and adaptive noise cancellation.',
		specs: ['Active Noise Cancellation', 'Spatial Audio', '20Hr Battery', 'Wireless Charging'],
		status: 'published'
	},
	{
		id: '3',
		image: gallery3,
		title: 'NeoBook Air',
		category: 'Computing',
		viewCount: 15890,
		likeCount: 1234,
		description: 'Ultra-thin laptop with powerful performance and all-day battery life.',
		specs: ['M3 Chip', '16GB RAM', '512GB SSD', '18Hr Battery'],
		status: 'published'
	},
	{
		id: '4',
		image: gallery4,
		title: 'Quantum Phone',
		category: 'Mobile',
		viewCount: 23456,
		likeCount: 1876,
		description: 'Revolutionary smartphone with quantum-enhanced processor and AI camera.',
		specs: ['Quantum Processor', '200MP Camera', '5G', '120Hz Display'],
		status: 'published'
	},
	{
		id: '5',
		image: gallery5,
		title: 'VR Headset X',
		category: 'Virtual Reality',
		viewCount: 9823,
		likeCount: 743,
		description: 'Immersive VR experience with ultra-high resolution and precision tracking.',
		specs: ['4K Per Eye', 'Inside-Out Tracking', 'Hand Tracking', 'Wireless'],
		status: 'draft'
	},
	{
		id: '6',
		image: gallery6,
		title: 'Smart Glasses',
		category: 'Augmented Reality',
		viewCount: 11234,
		likeCount: 921,
		description: 'Augmented reality glasses that blend digital content with the real world.',
		specs: ['AR Display', 'Voice Control', '8Hr Battery', 'UV Protection'],
		status: 'flagged'
	},
	{
		id: '7',
		image: gallery1,
		title: 'Pulse Band 3',
		category: 'Wearable Tech',
		viewCount: 7104,
		likeCount: 512,
		description: 'Lightweight fitness band with continuous heart-rate and sleep tracking.',
		specs: ['Heart-Rate Sensor', '10-Day Battery', 'Water Resistant', 'Sleep Tracking'],
		status: 'published'
	},
	{
		id: '8',
		image: gallery2,
		title: 'SoundCore Buds',
		category: 'Audio',
		viewCount: 6210,
		likeCount: 398,
		description: 'Compact earbuds tuned for clear mids and deep, controlled bass.',
		specs: ['Bass Boost', 'IPX5', '24Hr Case', 'Touch Controls'],
		status: 'published'
	},
	{
		id: '9',
		image: gallery3,
		title: 'NeoBook Studio',
		category: 'Computing',
		viewCount: 13102,
		likeCount: 1045,
		description: 'Creator-focused laptop with a color-accurate display and fast storage.',
		specs: ['M3 Pro Chip', '32GB RAM', '1TB SSD', 'Color-Accurate Display'],
		status: 'published'
	},
	{
		id: '10',
		image: gallery4,
		title: 'Quantum Phone Mini',
		category: 'Mobile',
		viewCount: 17890,
		likeCount: 1320,
		description: 'The compact Quantum Phone with the same AI camera in a smaller frame.',
		specs: ['Quantum Processor', '108MP Camera', '5G', 'Compact Frame'],
		status: 'published'
	},
	{
		id: '11',
		image: gallery5,
		title: 'VR Headset X Lite',
		category: 'Virtual Reality',
		viewCount: 5309,
		likeCount: 401,
		description: 'A lighter, more affordable entry point into the VR Headset X lineup.',
		specs: ['2K Per Eye', 'Inside-Out Tracking', 'Lightweight', 'Wireless'],
		status: 'published'
	},
	{
		id: '12',
		image: gallery6,
		title: 'Smart Glasses Air',
		category: 'Augmented Reality',
		viewCount: 8890,
		likeCount: 610,
		description: 'A slimmer take on Smart Glasses with all-day comfort in mind.',
		specs: ['AR Display', 'Voice Control', '10Hr Battery', 'UV Protection'],
		status: 'published'
	},
	{
		id: '13',
		image: gallery1,
		title: 'SmartWatch SE',
		category: 'Wearable Tech',
		viewCount: 9456,
		likeCount: 677,
		description: 'The essentials of SmartWatch Pro, refined into a more affordable package.',
		specs: ['AMOLED Display', '4-Day Battery', 'Water Resistant', 'Heart-Rate Monitor'],
		status: 'published'
	},
	{
		id: '14',
		image: gallery3,
		title: 'NeoBook Flex',
		category: 'Computing',
		viewCount: 10233,
		likeCount: 803,
		description: 'A 2-in-1 convertible laptop built for sketching, notes, and everyday work.',
		specs: ['M3 Chip', '16GB RAM', '360° Hinge', 'Stylus Support'],
		status: 'published'
	}
];

export const siteStats = {
	jobsCompleted: 1280,
	customers: 640,
	activeUsers: 312
};

export const testimonials: Testimonial[] = [
	{
		id: 1,
		name: 'Lena Ortiz',
		role: 'Creative Director, Studio Lumen',
		initials: 'LO',
		quote:
			'EddyArt Gallery made licensing images for our catalog effortless. The turnaround from inquiry to delivery was faster than any vendor we had used before.',
		rating: 5
	},
	{
		id: 2,
		name: 'Omar Haddad',
		role: 'Founder, Haddad Design Co.',
		initials: 'OH',
		quote:
			'The curation quality is what sold me. Every piece we have licensed has fit our brand perfectly, and the support team is genuinely responsive.',
		rating: 5
	},
	{
		id: 3,
		name: 'Priya Nair',
		role: 'Product Marketing Lead',
		initials: 'PN',
		quote:
			'We use the gallery for every product launch now. It has become part of our workflow, not just a place we visit occasionally.',
		rating: 4
	},
	{
		id: 4,
		name: 'Jordan Blake',
		role: 'Independent Photographer',
		initials: 'JB',
		quote:
			'As a contributor, the platform is a joy to work with — clean dashboard, clear analytics, and payouts that always arrive on time.',
		rating: 5
	},
	{
		id: 5,
		name: 'Mike Johnson',
		role: 'Art Buyer, Northline Media',
		initials: 'MJ',
		quote:
			'Their collection covers exactly the kind of forward-looking tech imagery we struggle to find elsewhere. It has become our first stop.',
		rating: 4
	},
	{
		id: 6,
		name: 'Sarah Chen',
		role: 'UX Researcher',
		initials: 'SC',
		quote:
			'Browsing feels fast and the detail pages give me everything I need before I commit to an image. Small details, but they add up.',
		rating: 5
	}
];

export const mockComments: Record<string, CommentNode[]> = {
	1: [
		{
			id: '1',
			author: 'Sarah Chen',
			text: 'This looks absolutely incredible! The design is so sleek and futuristic.',
			timestamp: '2 hours ago',
			replies: [
				{
					id: '2',
					author: 'Mike Johnson',
					text: 'I agree! The specs are really impressive too.',
					timestamp: '1 hour ago',
					replies: []
				}
			]
		},
		{
			id: '3',
			author: 'Lena Ortiz',
			authorId: 'c1',
			text: 'Has anyone tried this yet? Would love real-world feedback on performance.',
			timestamp: '5 hours ago',
			replies: [
				{
					id: '4',
					author: 'Jordan Blake',
					text: "Yes! We tested it in-house — battery holds up well under daily use.",
					timestamp: '3 hours ago',
					replies: []
				}
			]
		}
	],
	4: [
		{
			id: '5',
			author: 'Lena Ortiz',
			authorId: 'c1',
			text: 'Does the Quantum Phone ship internationally? Looking to order from outside the US.',
			timestamp: '1 day ago',
			replies: []
		}
	]
};

export const mockStaff: AppUser[] = [
	{ id: 'u2', email: 'jordan@nexusgallery.app', name: 'Jordan Blake', role: 'staff', avatarInitials: 'JB' },
	{ id: 'u3', email: 'priya@nexusgallery.app', name: 'Priya Nair', role: 'staff', avatarInitials: 'PN' }
];

export const mockAdminUser: AppUser = {
	id: 'u1',
	email: 'admin@nexusgallery.app',
	name: 'Admin',
	role: 'admin',
	avatarInitials: 'AD'
};

// Demo customer account — log in at /login with this email, any password 8+ chars.
export const mockCustomers: AppUser[] = [
	{ id: 'c1', email: 'lena@example.com', name: 'Lena Ortiz', role: 'customer', avatarInitials: 'LO' }
];

/**
 * Shared conversation threads. Admin's Requests page and the customer's
 * Inbox both render from this same array — there is exactly one thread
 * per conversation, not a copy on each side.
 */
export const mockConversations: BusinessConversation[] = [
	{
		id: '1',
		customerId: 'c1',
		customerName: 'Lena Ortiz',
		customerEmail: 'lena@example.com',
		subject: 'Bulk licensing inquiry',
		status: 'in_progress',
		updatedAt: '2026-07-21T14:12:00Z',
		messages: [
			{
				id: '1',
				senderRole: 'customer',
				senderName: 'Lena Ortiz',
				text: 'Interested in licensing 12 images for a print catalog. What are your commercial terms?',
				timestamp: '2026-07-21T14:12:00Z'
			},
			{
				id: '2',
				senderRole: 'admin',
				senderName: 'Admin',
				text: 'Thanks for reaching out — commercial licensing starts at $80/image for print use. Sending the full rate sheet by email shortly.',
				timestamp: '2026-07-21T16:40:00Z'
			}
		]
	},
	{
		id: '2',
		customerId: 'c2',
		customerName: 'Omar Haddad',
		customerEmail: 'omar@studiolumen.io',
		subject: 'Partnership proposal',
		status: 'resolved',
		updatedAt: '2026-07-19T09:03:00Z',
		messages: [
			{
				id: '1',
				senderRole: 'customer',
				senderName: 'Omar Haddad',
				text: 'We run a design studio and would love to feature your gallery in a joint showcase.',
				timestamp: '2026-07-19T09:03:00Z'
			},
			{
				id: '2',
				senderRole: 'staff',
				senderName: 'Priya Nair',
				text: "We'd love that too — I've forwarded this to our partnerships lead, expect an email this week.",
				timestamp: '2026-07-19T12:15:00Z'
			}
		]
	}
];

export const mockNotifications: AppNotification[] = [
	{
		id: 1,
		userId: 'c1',
		type: 'comment_reply',
		message: 'Jordan Blake replied to your comment on SmartWatch Pro',
		href: '/image/1',
		read: false,
		timestamp: '2026-07-22T09:10:00Z'
	},
	{
		id: 2,
		userId: 'c1',
		type: 'conversation_reply',
		message: 'Admin replied to your licensing inquiry',
		href: '/dashboard/inbox',
		read: false,
		timestamp: '2026-07-21T16:40:00Z'
	},
	{
		id: 3,
		userId: 'c1',
		type: 'system',
		message: 'Welcome to EddyArt Gallery — complete your profile to get started.',
		href: '/dashboard',
		read: true,
		timestamp: '2026-07-15T10:00:00Z'
	}
];
