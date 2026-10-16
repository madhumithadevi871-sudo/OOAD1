USE tour_travel_booking;
INSERT IGNORE INTO destinations(name,region,country,description,image_url) VALUES
('Ooty','Tamil Nadu','India','Tea gardens, mountain railways and cool Nilgiri views.','https://images.unsplash.com/photo-1596176530529-78163a4f7af2?auto=format&fit=crop&w=900&q=80'),
('Kodaikanal','Tamil Nadu','India','A hill station known for its lake, forests and walks.','https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=900&q=80'),
('Munnar','Kerala','India','Tea estates, mountain scenery and nature trails.','https://images.unsplash.com/photo-1605640840605-14ac1855827b?auto=format&fit=crop&w=900&q=80'),
('Goa','Goa','India','Beaches, heritage neighbourhoods and local food.','https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=900&q=80'),
('Manali','Himachal Pradesh','India','Himalayan landscapes, culture and outdoor excursions.','https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=900&q=80'),
('Mysuru','Karnataka','India','Palaces, markets and historic city sights.','https://images.unsplash.com/photo-1600112356915-089abb8fc71a?auto=format&fit=crop&w=900&q=80'),
('Madurai','Tamil Nadu','India','Historic temples, architecture and Tamil cuisine.','https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=900&q=80'),
('Coorg','Karnataka','India','Coffee country, waterfalls and forest landscapes.','https://images.unsplash.com/photo-1511497584788-876760111969?auto=format&fit=crop&w=900&q=80'),
('Chennai','Tamil Nadu','India','Coastal city, museums and South Indian food.','https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=900&q=80'),
('Kerala','Kerala','India','Backwaters, cultural sites and tropical landscapes.','https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=900&q=80');
INSERT INTO tour_packages(destination_id,title,description,duration_days,duration_nights,price_per_person,maximum_capacity,available_seats,inclusions,exclusions,accommodation_details,transport_details,status)
SELECT id,CONCAT(name,' Discovery'),CONCAT('A flexible guided introduction to ',name,'. Price shown per traveller; dates and services are confirmed during booking.'),3,2,8999.00,20,20,'Accommodation estimate, local sightseeing','Personal expenses, meals not listed','Standard category, subject to confirmation','Shared vehicle estimate','active' FROM destinations WHERE name IN ('Ooty','Munnar','Goa','Mysuru');
