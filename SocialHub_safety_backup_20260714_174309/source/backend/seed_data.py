"""
Seed script to populate the database with sample data:
- 100 user profiles with profile pictures
- 100 posts with images
- 10 reels
- Stories, followers, etc.
"""
import os
import sys
import random
import uuid
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.models import (
    User, Profile, Post, PostImage, Story, Reel,
    Follower, Like, Comment, StoryReaction, ReelLike,
    Chat, Message, Notification, chat_participants
)
from app.utils.security import hash_password

# First create all tables
Base.metadata.create_all(bind=engine)

# Sample data
FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James",
    "Isabella", "Oliver", "Mia", "Benjamin", "Charlotte", "Elijah", "Amelia",
    "Lucas", "Harper", "Mason", "Evelyn", "Logan", "Abigail", "Alexander",
    "Emily", "Ethan", "Elizabeth", "Jacob", "Sofia", "Michael", "Avery",
    "Daniel", "Ella", "Henry", "Madison", "Jackson", "Scarlett", "Sebastian",
    "Victoria", "Aiden", "Aria", "Matthew", "Grace", "Samuel", "Chloe",
    "David", "Penelope", "Joseph", "Layla", "Carter", "Riley", "Owen",
    "Aarav", "Priya", "Rahul", "Ananya", "Arjun", "Diya", "Rohan",
    "Kavya", "Aditya", "Meera", "Vikram", "Nisha", "Sanjay", "Pooja",
    "Ravi", "Sneha", "Amit", "Ritu", "Raj", "Shreya", "Aman", "Neha",
    "Kiran", "Deepa", "Nitin", "Komal", "Suresh", "Jyoti", "Gaurav",
    "Swati", "Manoj", "Reena", "Pankaj", "Sunita", "Dev", "Asha",
    "Vijay", "Lata", "Mohit", "Usha", "Sachin", "Geeta", "Anil",
    "Suman", "Tarun", "Kavita", "Hrithik", "Sapna", "Jay", "Pallavi"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas",
    "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
    "Clark", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Reddy",
    "Joshi", "Nair", "Mehta", "Desai", "Pandey", "Tiwari", "Mishra",
    "Rao", "Iyer", "Chowdhury", "Banerjee", "Mukherjee", "Sen",
    "Bose", "Das", "Ghosh", "Dutta", "Mitra", "Pal", "Saha"
]

BIOS = [
    "Living life to the fullest ✨ | Travel lover | Coffee addict",
    "Software developer by day, photographer by night 📸",
    "Fitness enthusiast 💪 | Healthy lifestyle advocate",
    "Foodie | Traveler | Dreamer | Making memories",
    "Entrepreneur | Building the future 🚀",
    "Artist | Creator | Dreamer",
    "Nature lover 🌿 | Hiking enthusiast",
    "Music is my therapy 🎵 | Guitar player",
    "Book worm 📚 | Knowledge seeker",
    "Dog dad 🐕 | Adventure awaits",
    "Chef in the making 👨‍🍳 | Recipe creator",
    "Yoga instructor | Mindfulness advocate 🧘",
    "Digital marketer | Social media expert 📱",
    "Photographer | Visual storyteller 📷",
    "Student | Learning every day 📖",
    "Sports fan | Weekend warrior ⚽",
    "Tech geek | AI enthusiast 🤖",
    "Minimalist | Living with less",
    "Fashion lover 👗 | Style blogger",
    "Gamer | Content creator 🎮",
    "Architecture lover | Design enthusiast",
    "Science nerd 🔬 | Research enthusiast",
    "Startup founder | Innovator",
    "Travel blogger | Exploring the world 🌍",
    "Music producer | Beat maker 🎹",
    "Film enthusiast | Movie critic 🎬",
    "Environmental activist 🌱 | Green living",
    "Coffee connoisseur ☕ | Café reviewer",
    "Cat person 🐱 | Animal lover",
    "Astronomy geek 🔭 | Stargazer"
]

LOCATIONS = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "San Francisco", "Seattle", "Boston", "Miami", "Denver",
    "London", "Paris", "Tokyo", "Sydney", "Toronto",
    "Mumbai", "Delhi", "Bangalore", "Pune", "Chennai",
    "Berlin", "Amsterdam", "Barcelona", "Rome", "Dubai",
    "Singapore", "Hong Kong", "Seoul", "Bangkok", "Istanbul"
]

POST_CONTENTS = [
    "Just had an amazing day at the beach! 🏖️ #beachlife #summer",
    "Beautiful sunset today 🌅 #sunset #photography",
    "Coffee and code ☕💻 #developer #coding",
    "New recipe turned out great! 🍝 #foodie #homecooking",
    "Morning workout done! 💪 #fitness #gym",
    "Exploring new places today 🗺️ #travel #adventure",
    "This book is incredible 📖 #bookworm #reading",
    "Happy with this purchase! 🛍️ #shopping #new",
    "Great meeting today 🤝 #business #entrepreneur",
    "Weekend vibes ✌️ #weekend #relax",
    "Throwback to last summer 🌞 #throwback",
    "New project launched! 🚀 #startup #launch",
    "Family time is the best time 👨‍👩‍👧‍👦 #family",
    "Concert was amazing last night! 🎸 #music #live",
    "Cooking my favorite dish tonight 🍳 #homemade",
    "Working from my favorite café ☕ #remotework",
    "Nature walk therapy 🌲 #nature #hiking",
    "Productivity mode ON 🎯 #goals #motivation",
    "Sunday brunch 🥞 #foodie #brunch",
    "Art museum visit today 🎨 #art #culture",
    "Gym gains 💪 #fitness #transformation",
    "Beach sunset vibes 🌅 #ocean #peaceful",
    "Street food exploration 🍜 #foodtour",
    "Photography session 📸 #portrait #model",
    "New outfit check 👗 #fashion #ootd",
    "Movie marathon tonight 🍿 #movienight",
    "Travel day! ✈️ #airport #wanderlust",
    "Yoga and meditation 🧘 #wellness #mindfulness",
    "Birthday celebration! 🎂 #birthday #party",
    "Golden hour magic ✨ #goldenhour #photography"
]

HASHTAGS = [
    ["photography", "sunset"], ["travel", "adventure"], ["food", "cooking"],
    ["fitness", "health"], ["tech", "coding"], ["fashion", "style"],
    ["nature", "outdoors"], ["music", "live"], ["art", "creative"],
    ["startup", "business"], ["coffee", "morning"], ["books", "reading"],
    ["pets", "animals"], ["sports", "fitness"], ["beach", "ocean"],
    ["city", "urban"], ["yoga", "wellness"], ["film", "cinema"],
    ["architecture", "design"], ["family", "love"]
]

REEL_CAPTIONS = [
    "This trick will blow your mind! 🤯 #lifehack #viral",
    "Dance moves 💃🕺 #dance #trending",
    "Cooking a 5-min meal 🍳 #recipe #quick",
    "My workout routine 💪 #fitness #gym",
    "Travel montage ✈️ #travel #adventure",
    "Morning routine ☀️ #routine #morning",
    "DIY project complete! 🔨 #diy #creative",
    "Guitar solo 🎸 #music #guitar",
    "Art timelapse 🎨 #art #timelapse",
    "Nature sounds 🌿 #nature #relaxing"
]


def download_placeholder_image(url: str, filepath: str) -> bool:
    try:
        urllib.request.urlretrieve(url, filepath)
        return True
    except Exception as e:
        print(f"  Warning: Could not download {url}: {e}")
        return False


def create_placeholder_svg(filepath: str, text: str, size: int = 200):
    """Create a simple SVG placeholder image."""
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
              "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"]
    color = random.choice(colors)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}">
  <rect width="{size}" height="{size}" fill="{color}"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
        font-family="Arial" font-size="14" fill="white">{text}</text>
</svg>"""
    with open(filepath, 'w') as f:
        f.write(svg)


def seed():
    db = SessionLocal()

    try:
        # Clean existing data
        db.query(StoryReaction).delete()
        db.query(Like).delete()
        db.query(Comment).delete()
        db.query(ReelLike).delete()
        db.query(PostImage).delete()
        db.query(Follower).delete()
        db.query(Story).delete()
        db.query(Reel).delete()
        db.query(Post).delete()
        db.query(Profile).delete()
        db.query(User).delete()
        db.commit()
        print("Cleared existing data.")

        # Create upload directories
        base_upload = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "uploads")
        for d in ["profile_pics", "cover_photos", "post_images", "reels"]:
            os.makedirs(os.path.join(base_upload, d), exist_ok=True)

        default_password = hash_password("Password1")
        users = []

        # ========== CREATE 100 USERS WITH PROFILES ==========
        print("\nCreating 100 users with profiles...")
        for i in range(100):
            fname = FIRST_NAMES[i % len(FIRST_NAMES)]
            lname = LAST_NAMES[i % len(LAST_NAMES)]
            username = f"{fname.lower()}{lname.lower()}{i}"
            email = f"{username}@example.com"

            user = User(
                email=email,
                username=username,
                full_name=f"{fname} {lname}",
                hashed_password=default_password,
                is_active=True,
                is_verified=random.random() > 0.3,
                is_email_verified=True,
                account_type="public",
            )
            db.add(user)
            db.flush()

            # Create profile
            bio = random.choice(BIOS)
            location = random.choice(LOCATIONS)
            profile = Profile(
                user_id=user.id,
                bio=f"{bio} | {location}",
                location=location,
                profile_picture=f"profile_pics/{user.id}.svg",
                cover_photo=f"cover_photos/{user.id}.svg",
            )
            db.add(profile)

            # Create SVG profile picture
            profile_pic_path = os.path.join(base_upload, "profile_pics", f"{user.id}.svg")
            create_placeholder_svg(profile_pic_path, fname[0], 200)

            # Create SVG cover photo
            cover_path = os.path.join(base_upload, "cover_photos", f"{user.id}.svg")
            create_placeholder_svg(cover_path, f"{fname} {lname}", 800)

            users.append(user)

            if (i + 1) % 10 == 0:
                print(f"  Created {i + 1}/100 users with profiles")

        db.commit()
        print(f"✅ Created {len(users)} users with profiles")

        # ========== CREATE 100 POSTS WITH IMAGES ==========
        print("\nCreating 100 posts with images...")
        posts = []
        for i in range(100):
            author = random.choice(users)
            content = POST_CONTENTS[i % len(POST_CONTENTS)]
            hashtags = random.choice(HASHTAGS)

            post = Post(
                user_id=author.id,
                content=content,
                hashtags=hashtags,
                is_published=True,
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 168)),
            )
            db.add(post)
            db.flush()
            posts.append(post)

            # Add post image (SVG placeholder)
            img_filename = f"{post.id}.svg"
            img_path = os.path.join(base_upload, "post_images", img_filename)
            create_placeholder_svg(img_path, f"Post {i+1}", 400)

            post_image = PostImage(
                post_id=post.id,
                image_url=f"post_images/{img_filename}",
                is_video=False,
                order=0,
            )
            db.add(post_image)

            # Sometimes add a second image
            if random.random() > 0.6:
                img_filename2 = f"{post.id}_2.svg"
                img_path2 = os.path.join(base_upload, "post_images", img_filename2)
                create_placeholder_svg(img_path2, f"Pic {i+1}b", 400)
                post_image2 = PostImage(
                    post_id=post.id,
                    image_url=f"post_images/{img_filename2}",
                    is_video=False,
                    order=1,
                )
                db.add(post_image2)

            if (i + 1) % 10 == 0:
                print(f"  Created {i + 1}/100 posts")

        db.commit()
        print(f"✅ Created {len(posts)} posts with images")

        # ========== CREATE 10 REELS ==========
        print("\nCreating 10 reels...")
        reels = []
        for i in range(10):
            author = random.choice(users)
            reel = Reel(
                user_id=author.id,
                video_url=f"reels/sample_reel_{i+1}.svg",  # placeholder
                caption=REEL_CAPTIONS[i],
                hashtags=HASHTAGS[i % len(HASHTAGS)],
                views_count=random.randint(100, 50000),
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
            )
            db.add(reel)
            db.flush()
            reels.append(reel)

            # Create reel thumbnail
            thumbnail_path = os.path.join(base_upload, "reels", f"sample_reel_{i+1}.svg")
            create_placeholder_svg(thumbnail_path, f"Reel {i+1}", 300)

            if (i + 1) % 5 == 0:
                print(f"  Created {i + 1}/10 reels")

        db.commit()
        print(f"✅ Created {len(reels)} reels")

        # ========== CREATE FOLLOWERS ==========
        print("\nCreating follower relationships...")
        follow_count = 0
        for user in users:
            # Each user follows 3-15 random users
            num_follows = random.randint(3, 15)
            potential_follows = [u for u in users if u.id != user.id]
            followed_users = random.sample(potential_follows, min(num_follows, len(potential_follows)))

            for followed in followed_users:
                existing = db.query(Follower).filter(
                    Follower.follower_id == user.id,
                    Follower.following_id == followed.id
                ).first()
                if not existing:
                    follower = Follower(
                        follower_id=user.id,
                        following_id=followed.id,
                        is_pending=False,
                    )
                    db.add(follower)
                    follow_count += 1

            if follow_count % 500 == 0 and follow_count > 0:
                print(f"  Created {follow_count} follows...")

        db.commit()
        print(f"✅ Created {follow_count} follower relationships")

        # ========== CREATE LIKES ON POSTS ==========
        print("\nCreating likes on posts...")
        like_count = 0
        for post in posts:
            num_likes = random.randint(0, min(30, len(users)))
            likers = random.sample(users, min(num_likes, len(users)))
            for liker in likers:
                like = Like(
                    user_id=liker.id,
                    post_id=post.id,
                    reaction="like",
                )
                db.add(like)
                like_count += 1

        db.commit()
        print(f"✅ Created {like_count} post likes")

        # ========== CREATE COMMENTS ==========
        print("\nCreating comments...")
        comment_texts = [
            "Amazing! 🔥", "Love this! ❤️", "So beautiful!", "Incredible work!",
            "Goals! 💯", "Wow, this is great!", "Keep it up! 👏", "This made my day!",
            "Absolutely stunning!", "Need this in my life! 😍", "So inspiring!",
            "Thanks for sharing!", "Best post ever! ⭐", "You're amazing!",
            "This is everything! 🙌", "Can't stop looking at this!",
            "Perfection! ✨", "Living for this content!", "Tell me more!",
            "This is why I follow you! 👑", "Obsessed! 💕", "Wow!",
            "So cool! 😎", "Goals for real! 💪", "This just made me smile 😊"
        ]
        comment_count = 0
        for post in posts[:60]:  # Comments on first 60 posts
            num_comments = random.randint(1, 8)
            commenters = random.sample(users, min(num_comments, len(users)))
            for commenter in commenters:
                comment = Comment(
                    post_id=post.id,
                    user_id=commenter.id,
                    content=random.choice(comment_texts),
                    created_at=post.created_at + timedelta(minutes=random.randint(1, 60)),
                )
                db.add(comment)
                comment_count += 1

        db.commit()
        print(f"✅ Created {comment_count} comments")

        # ========== CREATE STORIES ==========
        print("\nCreating stories...")
        story_count = 0
        for user in users[:30]:  # 30 users have stories
            num_stories = random.randint(1, 3)
            for j in range(num_stories):
                story = Story(
                    user_id=user.id,
                    media_url=f"post_images/{user.id}_story_{j}.svg",
                    media_type="image",
                    caption=random.choice(["Vibes ✨", "Daily life 📸", "Mood 😊", "Behind the scenes 🎬", ""]),
                    expires_at=datetime.utcnow() + timedelta(hours=24),
                    created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 20)),
                )
                db.add(story)

                # Create story image
                story_path = os.path.join(base_upload, "post_images", f"{user.id}_story_{j}.svg")
                create_placeholder_svg(story_path, f"Story {j+1}", 400)
                story_count += 1

        db.commit()
        print(f"✅ Created {story_count} stories")

        # ========== CREATE CHATS AND MESSAGES ==========
        print("\nCreating chats and messages...")
        chat_count = 0
        message_count = 0
        for _ in range(20):
            num_participants = random.randint(2, 4)
            participants = random.sample(users, min(num_participants, len(users)))
            chat = Chat(
                is_group=num_participants > 2,
                name=f"Group {chat_count+1}" if num_participants > 2 else None,
                created_by=participants[0].id,
            )
            db.add(chat)
            db.flush()

            for p in participants:
                stmt = chat_participants.insert().values(chat_id=chat.id, user_id=p.id, joined_at=datetime.utcnow())
                db.execute(stmt)

            # Add messages
            num_messages = random.randint(3, 10)
            for j in range(num_messages):
                sender = random.choice(participants)
                msg = Message(
                    chat_id=chat.id,
                    sender_id=sender.id,
                    content=random.choice([
                        "Hey! How are you?",
                        "What's up?",
                        "Check this out!",
                        "Haha lol",
                        "Let's meet up",
                        "Can you help me with something?",
                        "Sounds good!",
                        "I'll get back to you later",
                        "Thanks!",
                        "No problem",
                        "See you soon",
                        "Great idea!",
                        "Let me think about it",
                        "Awesome!",
                        "Cool, thanks for sharing",
                    ]),
                    message_type="text",
                    is_read=random.random() > 0.3,
                    created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
                )
                if j == 0:
                    msg.created_at = datetime.utcnow() - timedelta(hours=random.randint(24, 72))
                db.add(msg)
                message_count += 1

            chat_count += 1

        db.commit()
        print(f"✅ Created {chat_count} chats with {message_count} messages")

        # ========== CREATE NOTIFICATIONS ==========
        print("\nCreating notifications...")
        notif_count = 0
        for user in users[:50]:
            num_notifs = random.randint(1, 5)
            for _ in range(num_notifs):
                actor = random.choice(users)
                if actor.id == user.id:
                    continue
                notif_type = random.choice(["like", "comment", "follow", "follow_request", "mention", "share"])
                notif = Notification(
                    user_id=user.id,
                    actor_id=actor.id,
                    type=notif_type,
                    message=random.choice([
                        f"{actor.username} liked your post",
                        f"{actor.username} commented on your post",
                        f"{actor.username} started following you",
                        f"{actor.username} mentioned you in a post",
                        f"{actor.username} shared your post",
                    ]),
                    reference_id=str(random.choice(posts).id) if posts else None,
                    reference_type="post",
                    is_read=random.random() > 0.5,
                    created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                )
                db.add(notif)
                notif_count += 1

        db.commit()
        print(f"✅ Created {notif_count} notifications")

        # ========== CREATE REEL LIKES ==========
        print("\nCreating reel likes...")
        reel_like_count = 0
        for reel in reels:
            num_likes = random.randint(5, 40)
            likers = random.sample(users, min(num_likes, len(users)))
            for liker in likers:
                rl = ReelLike(
                    reel_id=reel.id,
                    user_id=liker.id,
                )
                db.add(rl)
                reel_like_count += 1

        db.commit()
        print(f"✅ Created {reel_like_count} reel likes")

        # ========== SUMMARY ==========
        total_users = db.query(User).count()
        total_profiles = db.query(Profile).count()
        total_posts = db.query(Post).count()
        total_images = db.query(PostImage).count()
        total_stories = db.query(Story).count()
        total_reels = db.query(Reel).count()
        total_followers = db.query(Follower).count()
        total_likes = db.query(Like).count()
        total_comments = db.query(Comment).count()

        print("\n" + "="*50)
        print("🎉 SEED DATA CREATED SUCCESSFULLY!")
        print("="*50)
        print(f"  👤 Users:        {total_users}")
        print(f"  📋 Profiles:     {total_profiles}")
        print(f"  📝 Posts:        {total_posts}")
        print(f"  🖼️  Post Images:  {total_images}")
        print(f"  📖 Stories:      {total_stories}")
        print(f"  🎬 Reels:        {total_reels}")
        print(f"  👥 Followers:    {total_followers}")
        print(f"  ❤️  Likes:        {total_likes}")
        print(f"  💬 Comments:     {total_comments}")
        print("="*50)
        print(f"\n  Login credentials for ALL users:")
        print(f"  Email: <username>@example.com")
        print(f"  Password: Password1")
        print(f"  Example: {users[0].email} / Password1")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()