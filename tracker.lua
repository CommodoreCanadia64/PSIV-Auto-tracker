
memory.usememorydomain("M68K BUS")

local event_flags_start = 0xFFF100 
local chest_flags_start = 0xFFF120 
local world_index_addr   = 0xFFF400 
local inventory_start    = 0xFFF410 


local character_equip_slots = {
    0xFFF54C, 0xFFF54D, 0xFFF54E, 0xFFF54F,  -- Chaz
    0xFFF5CC, 0xFFF5CD, 0xFFF5CE, 0xFFF5CF,  -- Alys
    0xFFF64C, 0xFFF64D, 0xFFF64E, 0xFFF64F,  -- Hahn
    0xFFF6CC, 0xFFF6CD, 0xFFF6CE, 0xFFF6CF,  -- Rune 
    0xFFF74C, 0xFFF74D, 0xFFF74E, 0xFFF74F,  -- Gryz
    0xFFF7CC, 0xFFF7CD, 0xFFF7CE, 0xFFF7CF,  -- Rika
    0xFFF84C, 0xFFF84D, 0xFFF84E, 0xFFF84F,  -- Demi
    0xFFF8CC, 0xFFF8CD, 0xFFF8CE, 0xFFF8CF,  -- Wren
    0xFFF94C, 0xFFF94D, 0xFFF94E, 0xFFF94F,  -- Raja
    0xFFF9CC, 0xFFF9CD, 0xFFF9CE, 0xFFF9CF,  -- Kyra
    0xFFFA4C, 0xFFFA4D, 0xFFFA4E, 0xFFFA4F   -- Seth
}

local data_filename = "data.txt"

local IDs = {
    amber = 0x8A, hydro = 0x98, digger = 0x97, sword = 0x77, 
    aero = 0x8F, alsh = 0x8D, torch = 0x8E, wand = 0x39,
    sapphire = 0x91, plate = 0x9A, vahal = 0x99, machine = 0x94, mantle = 0x3A,
    p_ring = 0x9B, m_ring = 0x9C, d_ring = 0x9D, r_ring = 0x9E, a_ring = 0x9F, mahlay = 0xA0
}

while true do
    local res = { amber=0, hydro=0, digger=0, sword=0, aero=0, alsh=0, torch=0, wand=0, 
                  sapphire=0, plate=0, vahal=0, machine=0, mantle=0, p_ring=0, m_ring=0, 
                  d_ring=0, r_ring=0, a_ring=0, mahlay=0 }
    
    -- 1. Check Standard Shared Inventory
    for i = inventory_start, inventory_start + 39 do
        local val = memory.read_u8(i)
        for name, id in pairs(IDs) do
            if val == id then
                if name == "amber" then res.amber = res.amber + 1 else res[name] = 1 end
            end
        end
    end

    -- 2. Scan Character Equipment Slots 
    for _, addr in ipairs(character_equip_slots) do
        local val = memory.read_u8(addr)
        for name, id in pairs(IDs) do
            if name ~= "amber" and val == id then
                res[name] = 1
            end
        end
    end

    local q_flags = {}
    for i = 0, 100 do q_flags[i+1] = memory.read_u8(event_flags_start + i) end

    local c_flags = {}
    for i = 0, 31 do c_flags[i+1] = memory.read_u8(chest_flags_start + i) end

    local world = memory.read_u8(world_index_addr)

    local file = io.open(data_filename, "w")
    if file then
        local out = string.format("%d,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d", 
            world, 
            table.concat(q_flags, ","), 
            table.concat(c_flags, ","),
            res.amber, res.hydro, res.digger, res.sword, res.aero, res.alsh, res.torch, 
            res.wand, res.sapphire, res.plate, res.vahal, res.machine, res.mantle,
            res.p_ring, res.m_ring, res.d_ring, res.r_ring, res.a_ring, res.mahlay)
        file:write(out)
        file:close()
    end
    emu.frameadvance()
end
